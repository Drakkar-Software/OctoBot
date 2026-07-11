#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import mock
import pytest

import octobot_commons.channels_name as channels_name
import octobot_commons.constants as common_constants
import octobot_commons.enums as common_enums
import octobot_evaluators.enums as evaluators_enums
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.modes as modes

from tests import event_loop
from tests.exchanges import simulated_exchange_manager, simulated_trader


def _get_trading_mode(simulated_trader_fixture):
    config, exchange_manager_inst, trader_inst = simulated_trader_fixture
    trading_mode = modes.AbstractTradingMode(config, exchange_manager_inst)
    exchange_manager_inst.trading_modes.append(trading_mode)
    trading_mode.trading_config = {}
    return trading_mode


def _build_producer(exchange_manager, trading_mode):
    producer = modes.AbstractTradingModeProducer(
        mock.Mock(), exchange_manager.config, trading_mode, exchange_manager
    )
    producer.matrix_id = "test-matrix-id"
    producer.exchange_name = exchange_manager.exchange_name
    return producer


def _mock_channel():
    channel = mock.Mock()
    consumer = mock.Mock()
    channel.new_consumer = mock.AsyncMock(return_value=consumer)
    return channel, consumer


def _set_relevant_time_frames(producer, time_frames):
    producer.exchange_manager.exchange_config.get_relevant_time_frames = mock.Mock(
        return_value=time_frames
    )


class TestGetTimeFrameFilter:
    def test_returns_mode_time_frame_when_wildcard(self, simulated_trader):
        trading_mode = _get_trading_mode(simulated_trader)
        trading_mode.time_frame = common_enums.TimeFrames.ONE_HOUR
        producer = _build_producer(trading_mode.exchange_manager, trading_mode)
        with mock.patch.object(producer, "is_time_frame_wildcard", mock.Mock(return_value=True)):
            assert producer._get_time_frame_filter(["4h"]) == ["1h"]

    def test_returns_matching_relevant_time_frames(self, simulated_trader):
        trading_mode = _get_trading_mode(simulated_trader)
        producer = _build_producer(trading_mode.exchange_manager, trading_mode)
        _set_relevant_time_frames(
            producer,
            [common_enums.TimeFrames.ONE_HOUR, common_enums.TimeFrames.FOUR_HOURS],
        )
        with mock.patch.object(producer, "is_time_frame_wildcard", mock.Mock(return_value=False)):
            assert producer._get_time_frame_filter(["1h"]) == ["1h"]

    def test_returns_all_relevant_when_trigger_is_wildcard(self, simulated_trader):
        trading_mode = _get_trading_mode(simulated_trader)
        producer = _build_producer(trading_mode.exchange_manager, trading_mode)
        _set_relevant_time_frames(
            producer,
            [common_enums.TimeFrames.ONE_HOUR, common_enums.TimeFrames.FOUR_HOURS],
        )
        with mock.patch.object(producer, "is_time_frame_wildcard", mock.Mock(return_value=False)):
            assert producer._get_time_frame_filter(common_constants.CONFIG_WILDCARD) == ["1h", "4h"]

    def test_returns_none_when_no_match(self, simulated_trader):
        trading_mode = _get_trading_mode(simulated_trader)
        producer = _build_producer(trading_mode.exchange_manager, trading_mode)
        _set_relevant_time_frames(producer, [common_enums.TimeFrames.FOUR_HOURS])
        with mock.patch.object(producer, "is_time_frame_wildcard", mock.Mock(return_value=False)):
            assert producer._get_time_frame_filter(["1h"]) is None

    def test_ignores_mode_time_frame_when_not_wildcard(self, simulated_trader):
        trading_mode = _get_trading_mode(simulated_trader)
        trading_mode.time_frame = common_enums.TimeFrames.ONE_HOUR
        producer = _build_producer(trading_mode.exchange_manager, trading_mode)
        _set_relevant_time_frames(
            producer,
            [common_enums.TimeFrames.ONE_HOUR, common_enums.TimeFrames.FOUR_HOURS],
        )
        with mock.patch.object(producer, "is_time_frame_wildcard", mock.Mock(return_value=False)):
            assert producer._get_time_frame_filter(["4h"]) == ["4h"]


class TestSubscribeToRegistrationTopic:
    pytestmark = pytest.mark.asyncio

    async def test_matrix_subscription_uses_wildcard_time_frame(self, simulated_trader):
        trading_mode = _get_trading_mode(simulated_trader)
        producer = _build_producer(trading_mode.exchange_manager, trading_mode)
        producer.time_frame_filter = ["1h"]
        matrix_channel, matrix_consumer = _mock_channel()
        matrix_topic = channels_name.OctoBotEvaluatorsChannelsName.MATRIX_CHANNEL.value
        with mock.patch.object(producer, "is_time_frame_wildcard", mock.Mock(return_value=True)), \
             mock.patch(
                 "octobot_evaluators.evaluators.channel.get_chan",
                 mock.Mock(return_value=matrix_channel),
             ) as get_matrix_chan_mock:
            await producer._subscribe_to_registration_topic(
                [matrix_topic], "BTC", "BTC/USDT"
            )
        get_matrix_chan_mock.assert_called_once_with(matrix_topic, producer.matrix_id)
        matrix_channel.new_consumer.assert_awaited_once_with(
            callback=producer.get_callback(matrix_topic),
            priority_level=producer.priority_level,
            matrix_id=producer.matrix_id,
            cryptocurrency="BTC",
            symbol="BTC/USDT",
            evaluator_type=evaluators_enums.EvaluatorMatrixTypes.STRATEGIES.value,
            exchange_name=producer.exchange_name,
            time_frame=common_constants.CONFIG_WILDCARD,
            supervised=trading_mode.exchange_manager.is_backtesting,
        )
        assert producer.evaluator_consumers == [(matrix_consumer, matrix_topic)]
        assert trading_mode.is_triggered_after_candle_close is False

    async def test_matrix_subscription_uses_time_frame_filter_when_not_wildcard(self, simulated_trader):
        trading_mode = _get_trading_mode(simulated_trader)
        producer = _build_producer(trading_mode.exchange_manager, trading_mode)
        producer.time_frame_filter = ["1h"]
        matrix_channel, _ = _mock_channel()
        matrix_topic = channels_name.OctoBotEvaluatorsChannelsName.MATRIX_CHANNEL.value
        with mock.patch.object(producer, "is_time_frame_wildcard", mock.Mock(return_value=False)), \
             mock.patch(
                 "octobot_evaluators.evaluators.channel.get_chan",
                 mock.Mock(return_value=matrix_channel),
             ):
            await producer._subscribe_to_registration_topic(
                [matrix_topic], "BTC", "BTC/USDT"
            )
        matrix_channel.new_consumer.assert_awaited_once_with(
            callback=producer.get_callback(matrix_topic),
            priority_level=producer.priority_level,
            matrix_id=producer.matrix_id,
            cryptocurrency="BTC",
            symbol="BTC/USDT",
            evaluator_type=evaluators_enums.EvaluatorMatrixTypes.STRATEGIES.value,
            exchange_name=producer.exchange_name,
            time_frame=["1h"],
            supervised=trading_mode.exchange_manager.is_backtesting,
        )

    async def test_ohlcv_subscription_sets_triggered_after_candle_close(self, simulated_trader):
        trading_mode = _get_trading_mode(simulated_trader)
        producer = _build_producer(trading_mode.exchange_manager, trading_mode)
        producer.time_frame_filter = ["1h"]
        ohlcv_channel, ohlcv_consumer = _mock_channel()
        ohlcv_topic = channels_name.OctoBotTradingChannelsName.OHLCV_CHANNEL.value
        with mock.patch.object(
            exchanges_channel, "get_chan", mock.Mock(return_value=ohlcv_channel)
        ) as get_trading_chan_mock:
            await producer._subscribe_to_registration_topic(
                [ohlcv_topic], "BTC", "BTC/USDT"
            )
        get_trading_chan_mock.assert_called_once_with(
            ohlcv_topic, trading_mode.exchange_manager.id
        )
        ohlcv_channel.new_consumer.assert_awaited_once_with(
            callback=producer.get_callback(ohlcv_topic),
            priority_level=producer.priority_level,
            cryptocurrency="BTC",
            symbol="BTC/USDT",
            time_frame=["1h"],
        )
        assert producer.trading_consumers == [(ohlcv_consumer, ohlcv_topic)]
        assert trading_mode.is_triggered_after_candle_close is True

    async def test_trading_channel_uses_wildcard_when_filter_is_none(self, simulated_trader):
        trading_mode = _get_trading_mode(simulated_trader)
        producer = _build_producer(trading_mode.exchange_manager, trading_mode)
        producer.time_frame_filter = None
        kline_channel, _ = _mock_channel()
        kline_topic = channels_name.OctoBotTradingChannelsName.KLINE_CHANNEL.value
        with mock.patch.object(
            exchanges_channel, "get_chan", mock.Mock(return_value=kline_channel)
        ):
            await producer._subscribe_to_registration_topic(
                [kline_topic], "BTC", "BTC/USDT"
            )
        kline_channel.new_consumer.assert_awaited_once_with(
            callback=producer.get_callback(kline_topic),
            priority_level=producer.priority_level,
            cryptocurrency="BTC",
            symbol="BTC/USDT",
            time_frame=common_constants.CONFIG_WILDCARD,
        )

    async def test_matrix_import_error_is_logged(self, simulated_trader):
        trading_mode = _get_trading_mode(simulated_trader)
        producer = _build_producer(trading_mode.exchange_manager, trading_mode)
        matrix_topic = channels_name.OctoBotEvaluatorsChannelsName.MATRIX_CHANNEL.value
        with mock.patch(
            "octobot_evaluators.evaluators.channel.get_chan",
            mock.Mock(side_effect=ImportError("missing evaluators")),
        ), mock.patch.object(producer.logger, "error") as logger_error_mock:
            await producer._subscribe_to_registration_topic(
                [matrix_topic], "BTC", "BTC/USDT"
            )
        logger_error_mock.assert_called_once_with(
            f"Can't connect matrix channel on {producer.exchange_name}"
        )
        assert producer.evaluator_consumers == []
