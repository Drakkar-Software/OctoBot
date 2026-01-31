#  Drakkar-Software OctoBot-Tentacles
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
import decimal
import mock
import pytest
import os
import os.path
import asyncio
import pytest_asyncio

import async_channel.util as channel_util
import octobot_backtesting.api as backtesting_api
import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.tests.test_config as test_config
import octobot_evaluators.api as evaluators_api
import octobot_trading.api as trading_api
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_trading.exchanges as exchanges
import octobot_trading.signals as trading_signals
import tentacles.Trading.Mode as Mode
import tests.test_utils.config as test_utils_config
import tests.test_utils.test_exchanges as test_exchanges
import octobot_tentacles_manager.api as tentacles_manager_api

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def tools(symbol="BTC/USDT"):
    tentacles_manager_api.reload_tentacle_info()
    trader = None
    try:
        config = test_config.load_test_config()
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]["USDT"] = 1000
        exchange_manager = test_exchanges.get_test_exchange_manager(config, "binance")
        exchange_manager.tentacles_setup_config = test_utils_config.get_tentacles_setup_config()

        # use backtesting not to spam exchanges apis
        exchange_manager.is_simulated = True
        exchange_manager.is_backtesting = True
        exchange_manager.use_cached_markets = False
        backtesting = await backtesting_api.initialize_backtesting(
            config,
            exchange_ids=[exchange_manager.id],
            matrix_id=None,
            data_files=[
                os.path.join(test_config.TEST_CONFIG_FOLDER, "AbstractExchangeHistoryCollector_1586017993.616272.data")])
        exchange_manager.exchange = exchanges.ExchangeSimulator(exchange_manager.config,
                                                                exchange_manager,
                                                                backtesting)
        await exchange_manager.exchange.initialize()
        for exchange_channel_class_type in [exchanges_channel.ExchangeChannel, exchanges_channel.TimeFrameExchangeChannel]:
            await channel_util.create_all_subclasses_channel(exchange_channel_class_type, exchanges_channel.set_chan,
                                                             exchange_manager=exchange_manager)

        trader = exchanges.TraderSimulator(config, exchange_manager)
        await trader.initialize()

        mode = Mode.DailyTradingMode(config, exchange_manager)
        await mode.initialize()
        # add mode to exchange manager so that it can be stopped and freed from memory
        exchange_manager.trading_modes.append(mode)
        mode.get_trading_mode_consumers()[0].MAX_CURRENCY_RATIO = 1

        # set BTC/USDT price at 1000 USDT
        trading_api.force_set_mark_price(exchange_manager, symbol, 1000)

        yield mode.producers[0], mode.get_trading_mode_consumers()[0], trader
    finally:
        if trader:
            await _stop(trader)


async def _stop(trader):
    for importer in backtesting_api.get_importers(trader.exchange_manager.exchange.backtesting):
        await backtesting_api.stop_importer(importer)
    await trader.exchange_manager.exchange.backtesting.stop()
    await trader.exchange_manager.stop()


async def test_default_values(tools):
    producer, _, trader = tools
    assert producer.state is None


async def test_set_state(tools):
    currency = "BTC"
    symbol = "BTC/USDT"
    time_frame = "1h"
    producer, consumer, trader = tools

    with mock.patch.object(
        consumer.trading_mode, "create_order",
        mock.AsyncMock(wraps=consumer.trading_mode.create_order)
    ) as create_order_mock:
        producer.final_eval = trading_constants.ZERO
        await producer._set_state(currency, symbol, trading_enums.EvaluatorStates.NEUTRAL)
        assert producer.state == trading_enums.EvaluatorStates.NEUTRAL
        # create as task to allow creator's queue to get processed
        await asyncio.create_task(_check_open_orders_count(trader, 0))
        create_order_mock.assert_not_called()

        producer.final_eval = decimal.Decimal(-1)
        await producer._set_state(currency, symbol, trading_enums.EvaluatorStates.VERY_LONG)
        assert producer.state == trading_enums.EvaluatorStates.VERY_LONG
        _check_trades_count(trader, 0)
        # market order got filled
        await asyncio.create_task(_check_open_orders_count(trader, 0))
        _check_trades_count(trader, 1)
        create_order_mock.assert_called_once()
        assert create_order_mock.mock_calls[0].kwargs["dependencies"] == None
        create_order_mock.reset_mock()

        producer.final_eval = trading_constants.ZERO
        await producer._set_state(currency, symbol, trading_enums.EvaluatorStates.NEUTRAL)
        # create as task to allow creator's queue to get processed
        await asyncio.create_task(_check_open_orders_count(trader, 0))
        create_order_mock.assert_not_called()

        producer.final_eval = trading_constants.ONE
        await producer._set_state(currency, symbol, trading_enums.EvaluatorStates.VERY_SHORT)
        assert producer.state == trading_enums.EvaluatorStates.VERY_SHORT
        # create as task to allow creator's queue to get processed
        await asyncio.create_task(_check_open_orders_count(trader, 0))
        # market order was created
        create_order_mock.assert_called_once()
        assert create_order_mock.mock_calls[0].kwargs["dependencies"] == None
        create_order_mock.reset_mock()
        # market order got filled
        _check_trades_count(trader, 2)

        producer.final_eval = trading_constants.ZERO
        await producer._set_state(currency, symbol, trading_enums.EvaluatorStates.NEUTRAL)
        assert producer.state == trading_enums.EvaluatorStates.NEUTRAL
        # create as task to allow creator's queue to get processed
        await asyncio.create_task(_check_open_orders_count(trader, 0))
        create_order_mock.assert_not_called()

        async def _cancel_symbol_open_orders(*args, **kwargs):
            await origin_cancel_symbol_open_orders(*args, **kwargs)
            return (
                True, 
                trading_signals.get_orders_dependencies([mock.Mock(order_id="123"), mock.Mock(order_id="456-cancel_symbol_open_orders")])
            )

        async def _apply_cancel_policies(*args, **kwargs):
            await origin_apply_cancel_policies(*args, **kwargs)
            return (
                True, 
                trading_signals.get_orders_dependencies([mock.Mock(order_id="456-cancel_policy")])
            )

        origin_cancel_symbol_open_orders = producer.cancel_symbol_open_orders
        origin_apply_cancel_policies = producer.apply_cancel_policies
        producer.final_eval = decimal.Decimal(str(-0.5))
        with mock.patch.object(
            producer, "cancel_symbol_open_orders",
            mock.AsyncMock(side_effect=_cancel_symbol_open_orders)
        ) as cancel_symbol_open_orders_mock, mock.patch.object(
            producer, "apply_cancel_policies",
            mock.AsyncMock(side_effect=_apply_cancel_policies)
        ) as apply_cancel_policies_mock:
            await producer._set_state(currency, symbol, trading_enums.EvaluatorStates.LONG)
            cancel_symbol_open_orders_mock.assert_called_once_with(symbol)
            cancel_symbol_open_orders_mock.reset_mock()
            apply_cancel_policies_mock.assert_called_once_with()
            apply_cancel_policies_mock.reset_mock()
            assert producer.state == trading_enums.EvaluatorStates.LONG
            # create as task to allow creator's queue to get processed
            await asyncio.create_task(_check_open_orders_count(trader, 1))
            create_order_mock.assert_called_once()
            # cancelled orders dependencies are forwarded to create_order
            expected_dependencies = trading_signals.get_orders_dependencies(
                [mock.Mock(order_id="456-cancel_policy"), mock.Mock(order_id="123"), mock.Mock(order_id="456-cancel_symbol_open_orders")]
            )
            assert create_order_mock.mock_calls[0].kwargs["dependencies"] == expected_dependencies
            create_order_mock.reset_mock()

            producer.final_eval = trading_constants.ZERO
            await producer._set_state(currency, symbol, trading_enums.EvaluatorStates.NEUTRAL)
            cancel_symbol_open_orders_mock.assert_not_called()
            apply_cancel_policies_mock.assert_not_called()
            assert producer.state == trading_enums.EvaluatorStates.NEUTRAL
            # create as task to allow creator's queue to get processed
            await asyncio.create_task(_check_open_orders_count(trader, 1))
            create_order_mock.assert_not_called()

            producer.final_eval = decimal.Decimal(str(0.5))
            await producer._set_state(currency, symbol, trading_enums.EvaluatorStates.SHORT)
            apply_cancel_policies_mock.assert_called_once_with()
            apply_cancel_policies_mock.reset_mock()
            cancel_symbol_open_orders_mock.assert_called_once_with(symbol)
            cancel_symbol_open_orders_mock.reset_mock()
            assert producer.state == trading_enums.EvaluatorStates.SHORT
            # let both other be created
            await asyncio_tools.wait_asyncio_next_cycle()
            # create as task to allow creator's queue to get processed
            await asyncio.create_task(_check_open_orders_count(trader, 2))  # has stop loss
            assert create_order_mock.call_count == 2
            # cancelled orders dependencies are forwarded to all created orders
            assert create_order_mock.mock_calls[0].kwargs["dependencies"] == expected_dependencies
            assert create_order_mock.mock_calls[1].kwargs["dependencies"] == expected_dependencies
            create_order_mock.reset_mock()

            producer.final_eval = trading_constants.ZERO
            await producer._set_state(currency, symbol, trading_enums.EvaluatorStates.NEUTRAL)
            cancel_symbol_open_orders_mock.assert_not_called()
            apply_cancel_policies_mock.assert_not_called()
            assert producer.state == trading_enums.EvaluatorStates.NEUTRAL
            # create as task to allow creator's queue to get processed
            await asyncio.create_task(_check_open_orders_count(trader, 2))
            create_order_mock.assert_not_called()


async def test_get_delta_risk(tools):
    producer, consumer, trader = tools
    for i in range(0, 100, 1):
        trader.risk = decimal.Decimal(str(i / 100))
        assert round(producer._get_delta_risk(), 6) \
               == round(decimal.Decimal(str(producer.RISK_THRESHOLD * i / 100)), 6)


async def test_create_state(tools):
    producer, consumer, trader = tools
    delta_risk = producer._get_delta_risk()
    for i in range(-100, 100, 1):
        producer.final_eval = decimal.Decimal(str(i / 100))
        await producer.create_state(None, None)
        if producer.final_eval < producer.VERY_LONG_THRESHOLD + delta_risk:
            assert producer.state == trading_enums.EvaluatorStates.VERY_LONG
        elif producer.final_eval < producer.LONG_THRESHOLD + delta_risk:
            assert producer.state == trading_enums.EvaluatorStates.LONG
        elif producer.final_eval < producer.NEUTRAL_THRESHOLD - delta_risk:
            assert producer.state == trading_enums.EvaluatorStates.NEUTRAL
        elif producer.final_eval < producer.SHORT_THRESHOLD - delta_risk:
            assert producer.state == trading_enums.EvaluatorStates.SHORT
        else:
            assert producer.state == trading_enums.EvaluatorStates.VERY_SHORT


async def test_set_final_eval(tools):
    currency = "BTC"
    symbol = "BTC/USDT"
    time_frame = "1h"
    producer, consumer, trader = tools
    matrix_id = evaluators_api.create_matrix()

    await producer._set_state(currency, symbol, trading_enums.EvaluatorStates.SHORT)
    assert producer.state == trading_enums.EvaluatorStates.SHORT
    # let both other be created
    await asyncio_tools.wait_asyncio_next_cycle()
    await asyncio.create_task(_check_open_orders_count(trader, 2))  # has stop loss
    producer.final_eval = "val"
    await producer.set_final_eval(matrix_id, currency, symbol, time_frame,
                                  commons_enums.TriggerSource.EVALUATION_MATRIX.value)
    assert producer.state == trading_enums.EvaluatorStates.SHORT  # ensure did not change trading_enums.EvaluatorStates
    assert producer.final_eval == "val"  # ensure did not change trading_enums.EvaluatorStates
    await asyncio.create_task(_check_open_orders_count(trader, 2))  # ensure did not change orders


async def test_finalize(tools):
    currency = "BTC"
    symbol = "BTC/USDT"
    producer, consumer, trader = tools
    matrix_id = evaluators_api.create_matrix()

    await producer.finalize(trading_api.get_exchange_name(trader.exchange_manager), matrix_id, currency, symbol)
    assert producer.final_eval == trading_constants.ZERO

    await producer._set_state(currency, symbol, trading_enums.EvaluatorStates.SHORT)
    assert producer.state == trading_enums.EvaluatorStates.SHORT
    # let both other be created
    await asyncio_tools.wait_asyncio_next_cycle()
    await asyncio.create_task(_check_open_orders_count(trader, 2))  # has stop loss

    await producer._set_state(currency, symbol, trading_enums.EvaluatorStates.SHORT)
    await asyncio.create_task(
        _check_open_orders_count(trader, 2))  # ensure did not change orders because neutral state


async def _check_open_orders_count(trader, count):
    assert len(trading_api.get_open_orders(trader.exchange_manager)) == count


def _check_trades_count(trader, count):
    assert len(trading_api.get_trade_history(trader.exchange_manager)) == count
