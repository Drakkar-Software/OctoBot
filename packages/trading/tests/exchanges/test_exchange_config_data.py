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
import pytest
import mock

from tests import event_loop
from octobot_commons.tests.test_config import load_test_config
from octobot_commons.constants import CONFIG_CRYPTO_CURRENCIES
from octobot_commons.enums import TimeFrames
from octobot_trading.exchanges.exchange_manager import ExchangeManager
from octobot_trading.api.exchange import cancel_ccxt_throttle_task
import octobot_trading.exchange_channel as exchange_channel
import octobot_trading.constants as trading_constants

pytestmark = pytest.mark.asyncio


class TestExchangeConfig:
    EXCHANGE_NAME = "binanceus"

    @staticmethod
    async def init_default(config=None):
        if not config:
            config = load_test_config()

        exchange_manager = ExchangeManager(config, TestExchangeConfig.EXCHANGE_NAME)
        exchange_manager.exchange_config.realtime_data_fetching = True
        await exchange_manager.initialize(exchange_config_by_exchange=None)
        return config, exchange_manager

    async def test_traded_pairs(self):
        config = load_test_config()
        config[CONFIG_CRYPTO_CURRENCIES] = {
            "Avalanche": {
                "pairs": ["AVAX/BTC"]
            },
            "Ethereum": {
                "enabled": True,
                "pairs": ["ETH/USDT"]
            },
            "Uniswap": {
                "enabled": False,
                "pairs": ["UNI/BTC"]
            }
        }

        _, exchange_manager = await self.init_default(config=config)
        try:
            assert exchange_manager.exchange_config.traded_cryptocurrencies == {
                "Ethereum": ["ETH/USDT"],
                "Avalanche": ["AVAX/BTC"]
            }
            all_pairs = sorted(["AVAX/BTC", "ETH/USDT", "UNI/BTC"])
            all_enabled_pairs = sorted(["AVAX/BTC", "ETH/USDT"])
            assert sorted(exchange_manager.exchange_config.traded_symbol_pairs) == all_enabled_pairs
            cancel_ccxt_throttle_task()
        finally:
            await exchange_manager.stop()

    async def test_traded_pairs_with_wildcard(self):
        config = load_test_config()
        config[CONFIG_CRYPTO_CURRENCIES] = {
            "Bitcoin": {
                "pairs": ["*"],
                "quote": "BTC"
            },
            "Ethereum": {
                "enabled": False,
                "pairs": ["*"],
                "quote": "ETH"
            }
        }
        _, exchange_manager = await self.init_default(config=config)
        try:
            assert "AVAX/BTC" in exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"]
            assert "ADA/BTC" in exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"]
            assert "MATIC/BTC" in exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"]
            assert "ONT/BTC" not in exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"]
            assert "BTC/USDT" not in exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"]
            assert "ETH/USDT" not in exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"]
            assert "AVAX/BNB" not in exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"]
            assert "ETH/BTC" in exchange_manager.exchange_config.traded_symbol_pairs

            # inactive markets
            assert "UNI/BTC" not in exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"]

            # disabled
            assert "Ethereum" not in exchange_manager.exchange_config.traded_cryptocurrencies
            assert "ADA/ETH" not in exchange_manager.exchange_config.traded_symbol_pairs

            cancel_ccxt_throttle_task()
        finally:
            await exchange_manager.stop()

    async def test_traded_pairs_with_invalid_wildcard(self):
        config = load_test_config()

        # missing quote key
        config[CONFIG_CRYPTO_CURRENCIES] = {
            "Bitcoin": {
                "enabled": True,
                "pairs": ["*"],
                "quote": "BTC"
            },
            "Ethereum": {
                "pairs": ["*"],
            }
        }
        _, exchange_manager = await self.init_default(config=config)
        try:
            assert "ADA/BTC" in exchange_manager.exchange_config.traded_symbol_pairs
            assert "Bitcoin" in exchange_manager.exchange_config.traded_cryptocurrencies

            # inactive markets
            assert "TRX/BTC" not in exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"]

            # invalid ETH wildcard config
            assert "Ethereum" not in exchange_manager.exchange_config.traded_cryptocurrencies

            cancel_ccxt_throttle_task()
        finally:
            await exchange_manager.stop()

    async def test_traded_pairs_with_add(self):
        config = load_test_config()
        config[CONFIG_CRYPTO_CURRENCIES] = {
            "Bitcoin": {
                "pairs": ["*"],
                "quote": "BTC",
                "add": ["BTC/USDT"]
            },
            "Ethereum": {
                "enabled": False,
                "pairs": ["*"],
                "quote": "ETH",
                "add": ["ETH/USDT"]
            }
        }

        _, exchange_manager = await self.init_default(config=config)
        try:
            assert "AVAX/BTC" in exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"]
            assert "ADA/BTC" in exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"]
            assert "MATIC/BTC" in exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"]
            assert "LINK/BTC" in exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"]
            assert "ONT/BTC" not in exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"]
            assert "BTC/USDT" in exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"]
            assert "ETH/USDT" not in exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"]
            assert "AVAX/BNB" not in exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"]
            assert "BTC/USDT" in exchange_manager.exchange_config.traded_symbol_pairs

            # inactive markets
            assert "UNI/BTC" not in exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"]

            # disabled
            assert "Ethereum" not in exchange_manager.exchange_config.traded_cryptocurrencies
            assert "ADA/ETH" not in exchange_manager.exchange_config.traded_symbol_pairs
            assert "ETH/USDT" not in exchange_manager.exchange_config.traded_symbol_pairs
            cancel_ccxt_throttle_task()
        finally:
            await exchange_manager.stop()

    async def test_traded_pairs_with_redundancy(self):
        config = load_test_config()
        config[CONFIG_CRYPTO_CURRENCIES] = {
            "Binance Coin": {
                "pairs": [
                    "BNB/USDT"
                ]
            },
            "Binance USD": {
                "pairs": [
                    "BNB/BUSD"
                ]
            },
            "Bitcoin": {
                "enabled": True,
                "pairs": [
                    "BNB/BTC"
                ]
            },
            "Tether": {
                "enabled": True,
                "pairs": [
                    "BNB/USDT"
                ]
            }
        }

        _, exchange_manager = await self.init_default(config=config)
        try:
            assert exchange_manager.exchange_config.traded_cryptocurrencies["Binance Coin"] == ["BNB/USDT"]
            assert exchange_manager.exchange_config.traded_cryptocurrencies["Bitcoin"] == ["BNB/BTC"]
            assert exchange_manager.exchange_config.traded_cryptocurrencies["Tether"] == ["BNB/USDT"]

            # inactive markets
            assert exchange_manager.exchange_config.traded_cryptocurrencies["Binance USD"] == []

            sorted_pairs_without_redundancy = sorted(["BNB/USDT", "BNB/BTC"])
            assert sorted(exchange_manager.exchange_config.traded_symbol_pairs) == sorted_pairs_without_redundancy

            cancel_ccxt_throttle_task()
        finally:
            await exchange_manager.stop()

    @pytest.mark.parametrize("watch_only,added_pairs,removed_pairs,added_time_frames", [
        (False, ["ADA/USDT"], [], [TimeFrames.ONE_MINUTE, TimeFrames.THREE_MINUTES]),
        (True, ["ETH/USDT"], [], [TimeFrames.ONE_MINUTE, TimeFrames.THREE_MINUTES]),
        (False, ["ADA/USDT", "LINK/USDT"], [], []),
        (False, [], ["BTC/USDT"], [TimeFrames.ONE_MINUTE]),
        (True, [], ["BTC/USDT"], [TimeFrames.ONE_MINUTE]),
    ])
    async def test_update_traded_symbol_pairs(self, watch_only, added_pairs, removed_pairs, added_time_frames):
        expected_watch_only_modified_channels = [trading_constants.TICKER_CHANNEL]
        expected_traded_modified_channels = [
            trading_constants.TICKER_CHANNEL,
            trading_constants.OHLCV_CHANNEL,
            trading_constants.FUNDING_CHANNEL,
        ]
        config = load_test_config()
        config[CONFIG_CRYPTO_CURRENCIES] = {
            "Bitcoin": {
                "pairs": ["BTC/USDT"]
            }
        }
        _, exchange_manager = await self.init_default(config=config)
        try:
            assert exchange_manager.exchange_config.additional_time_frames == []
            # init additional_time_frames if a random time frame that is not in available time frames
            assert TimeFrames.ONE_YEAR not in exchange_manager.exchange_config.available_time_frames
            exchange_manager.exchange_config.additional_time_frames = [TimeFrames.ONE_YEAR]
            initial_available_time_frames = list(exchange_manager.exchange_config.available_time_frames)
            assert TimeFrames.ONE_MINUTE in initial_available_time_frames # 1m is already in available time frames
            assert TimeFrames.THREE_MINUTES not in initial_available_time_frames # 3m is NOT in available time frames
            new_added_time_frames = [tf for tf in added_time_frames if tf not in initial_available_time_frames]
            
            # Pre-populate lists for removal tests
            if removed_pairs:
                for pair in removed_pairs:
                    if pair not in exchange_manager.exchange_config.traded_symbol_pairs:
                        exchange_manager.exchange_config.traded_symbol_pairs.append(pair)
                if watch_only:
                    exchange_manager.exchange_config.additional_traded_pairs = removed_pairs.copy()
                    exchange_manager.exchange_config.watched_pairs = removed_pairs.copy()
                else:
                    exchange_manager.exchange_config.additional_traded_pairs = removed_pairs.copy()
            for channel in expected_traded_modified_channels:
                channel_instance = exchange_channel.get_chan(channel, exchange_manager.id)
                channel_instance.modify = mock.AsyncMock(wraps=channel_instance.modify)
            ohlcv_producer = exchange_channel.get_chan(
                trading_constants.OHLCV_CHANNEL, exchange_manager.id
            ).producers[0]
            ticker_producer = exchange_channel.get_chan(
                trading_constants.TICKER_CHANNEL, exchange_manager.id
            ).producers[0]
            with mock.patch.object(
                exchange_manager.exchange_config, '_is_valid_symbol', wraps=exchange_manager.exchange_config._is_valid_symbol
            ) as is_valid_mock, mock.patch.object(
                exchange_manager, 'time_frame_exists', wraps=exchange_manager.time_frame_exists
            ) as time_frame_exists_mock, mock.patch.object(
                ohlcv_producer, '_initialize', mock.AsyncMock()
            ) as ohlcv_updater_initialize_mock, mock.patch.object(
                ticker_producer, 'fetch_and_push_pair', mock.AsyncMock()
            ) as ticker_fetch_and_push_pair_mock, mock.patch.object(
                exchange_manager.exchange_config, '_logger', wraps=exchange_manager.exchange_config._logger
            ) as logger_mock:
                await exchange_manager.exchange_config.update_traded_symbol_pairs(
                    added_pairs=added_pairs,
                    removed_pairs=removed_pairs,
                    added_time_frames=added_time_frames,
                    watch_only=watch_only,
                )
                
                # Verify _is_valid_symbol was called for all pairs
                assert is_valid_mock.call_count == len(added_pairs) + len(removed_pairs)
                assert time_frame_exists_mock.call_count == len(new_added_time_frames)
                if added_pairs:
                    # ticker update called for each added pair, regardless of watch_only or not
                    assert sorted(
                        [call.args[0] for call in ticker_fetch_and_push_pair_mock.mock_calls]
                    ) == sorted(added_pairs)
                if watch_only:
                    ohlcv_updater_initialize_mock.assert_not_called()
                elif added_pairs:
                    # called once for config pairs, once for additional pairs
                    assert len(ohlcv_updater_initialize_mock.mock_calls) == 1
                    assert ohlcv_updater_initialize_mock.mock_calls[0].args == (
                        [pair for pair in added_pairs if pair not in exchange_manager.exchange_config.traded_symbol_pairs],
                        False
                    )
            
            if watch_only:
                # watched pairs should not have any additional time frames, even if provided
                assert exchange_manager.exchange_config.additional_time_frames == [TimeFrames.ONE_YEAR]
                for pair in added_pairs:
                    assert pair in exchange_manager.exchange_config.watched_pairs
                for pair in removed_pairs:
                    assert pair not in exchange_manager.exchange_config.watched_pairs
                self._assert_modified_channels(
                    exchange_manager.exchange_config, expected_watch_only_modified_channels, expected_traded_modified_channels
                )
            else:
                # additional traded pairs should have additional time frames if provided
                if added_time_frames and added_pairs:
                    assert exchange_manager.exchange_config.additional_time_frames == [TimeFrames.ONE_YEAR] + [
                        tf for tf in added_time_frames if tf not in initial_available_time_frames
                    ]
                else:
                    assert exchange_manager.exchange_config.additional_time_frames == [TimeFrames.ONE_YEAR]
                # initial available time frames should not have changed, only additional time frames can change
                assert exchange_manager.exchange_config.available_time_frames == initial_available_time_frames
                for pair in added_pairs:
                    assert pair in exchange_manager.exchange_config.additional_traded_pairs
                for pair in removed_pairs:
                    assert pair not in exchange_manager.exchange_config.additional_traded_pairs
                self._assert_modified_channels(
                    exchange_manager.exchange_config, expected_traded_modified_channels, expected_watch_only_modified_channels
                )

            # ensure no hidden error occured (due to the global error catching)
            if new_added_time_frames and watch_only:
                assert logger_mock.error.call_count == 1
                assert f"Ignored additional time frames for watched pairs" in logger_mock.error.call_args[0][0]
            else:
                assert logger_mock.error.call_count == 0

            # Test removed_traded_pairs
            if removed_pairs:
                # removed pairs should be tracked
                assert exchange_manager.exchange_config.removed_traded_pairs == removed_pairs

                # calling again with the same pairs should not change state for removed pairs
                before_second_call_removed = list(exchange_manager.exchange_config.removed_traded_pairs)
                await exchange_manager.exchange_config.update_traded_symbol_pairs(
                    added_pairs=removed_pairs,
                    removed_pairs=removed_pairs,
                    added_time_frames=added_time_frames,
                    watch_only=watch_only,
                )
                # removed_traded_pairs should remain unchanged
                assert exchange_manager.exchange_config.removed_traded_pairs == before_second_call_removed
                for pair in removed_pairs:
                    # removed pairs should not re-appear in additional_traded_pairs
                    assert pair not in exchange_manager.exchange_config.additional_traded_pairs
                    # and should not re-appear in watched_pairs for watch_only mode
                    if watch_only:
                        assert pair not in exchange_manager.exchange_config.watched_pairs
            else:
                # no removed pairs: tracking list must stay empty
                assert exchange_manager.exchange_config.removed_traded_pairs == []

            cancel_ccxt_throttle_task()
        finally:
            await exchange_manager.stop()
        
    async def test_update_traded_symbol_pairs_no_available_time_frames(self):
        config = load_test_config()
        config[CONFIG_CRYPTO_CURRENCIES] = {
            "Bitcoin": {
                "pairs": ["BTC/USDT"]
            }
        }
        _, exchange_manager = await self.init_default(config=config)
        try:
            exchange_manager.exchange_config.available_time_frames = []
            assert exchange_manager.exchange_config.additional_time_frames == []
            with mock.patch.object(
                exchange_manager.exchange_config, '_is_valid_symbol', wraps=exchange_manager.exchange_config._is_valid_symbol
            ) as is_valid_mock, mock.patch.object(
                exchange_manager, 'time_frame_exists', wraps=exchange_manager.time_frame_exists
            ) as time_frame_exists_mock, mock.patch.object(
                exchange_channel.get_chan(
                    trading_constants.OHLCV_CHANNEL, exchange_manager.id
                ).producers[0], '_initialize', mock.AsyncMock()
            ) as ohlcv_updater_initialize_mock, mock.patch.object(
                exchange_channel.get_chan(
                    trading_constants.TICKER_CHANNEL, exchange_manager.id
                ).producers[0], 'fetch_and_push_pair', mock.AsyncMock()
            ) as ticker_fetch_and_push_pair_mock, mock.patch.object(
                exchange_manager.exchange_config, '_logger', wraps=exchange_manager.exchange_config._logger
            ) as logger_mock:
                await exchange_manager.exchange_config.update_traded_symbol_pairs(
                    added_pairs=["ETH/USDT"],
                    removed_pairs=[],
                    added_time_frames=[TimeFrames.ONE_HOUR],
                    watch_only=False,
                )
                assert is_valid_mock.call_count == 1
                assert time_frame_exists_mock.call_count == 1
                ohlcv_updater_initialize_mock.assert_called_once_with(["ETH/USDT"], False)
                ticker_fetch_and_push_pair_mock.assert_called_once_with("ETH/USDT")
                assert logger_mock.error.call_count == 0
                assert exchange_manager.exchange_config.additional_time_frames == [TimeFrames.ONE_HOUR]
        finally:
            await exchange_manager.stop()

    def _assert_modified_channels(
        self, exchange_config, expected_modified_channels, expected_unmodified_channels
    ):
        unmodified_channels = [
            chan for chan in expected_unmodified_channels if chan not in expected_modified_channels
        ]
        for channel in expected_modified_channels:
            channel_instance = exchange_channel.get_chan(channel, exchange_config.exchange_manager.id)
            assert channel_instance.modify.call_count > 0, f"{channel} should have been modified"
        for channel in unmodified_channels:
            channel_instance = exchange_channel.get_chan(channel, exchange_config.exchange_manager.id)
            assert channel_instance.modify.call_count == 0, f"{channel} should not have been modified"
