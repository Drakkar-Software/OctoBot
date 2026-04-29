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
import time
import asyncio
import mock
import pytest
import decimal

import octobot_commons.constants as commons_constants
import octobot_commons.asyncio_tools as asyncio_tools
from octobot_backtesting.backtesting import Backtesting
from octobot_commons.tests.test_config import load_test_config
from octobot_trading.modes.channel.abstract_mode_consumer import AbstractTradingModeConsumer
from octobot_trading.constants import TRADING_MODE_ACTIVITY_REASON
from octobot_trading.exchanges.exchange_manager import ExchangeManager
from octobot_trading.modes import AbstractTradingMode, AbstractTradingModeProducer, TradingModeActivity
from octobot_trading.exchanges.traders.trader_simulator import TraderSimulator
import octobot_trading.personal_data as personal_data
import octobot_trading.enums
import octobot_trading.errors
from tests import event_loop

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def _get_tools():
    symbol = "BTC/USDT"
    config = load_test_config()
    config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]["SUB"] = \
        0.000000000000000000005
    config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]["BNB"] = \
        0.000000000000000000005
    config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]["USDT"] = 2000
    exchange_manager = ExchangeManager(config, "binanceus")

    # use backtesting not to spam exchanges apis
    exchange_manager.is_simulated = True
    exchange_manager.is_backtesting = True
    exchange_manager.use_cached_markets = False
    exchange_manager.backtesting = Backtesting(None, [exchange_manager.id], None, [], False)

    await exchange_manager.initialize(exchange_config_by_exchange=None)

    trader = TraderSimulator(config, exchange_manager)
    await trader.initialize()
    
    mode = AbstractTradingMode(config, exchange_manager)
    consumer = AbstractTradingModeConsumer(mode)

    return exchange_manager, symbol, consumer


async def test_can_create_order():
    _, symbol, consumer = await _get_tools()
    # portfolio: "BTC": 10 "USD": 1000
    not_owned_symbol = "ETH/BTC"
    not_owned_market = "BTC/ETH"
    min_trigger_symbol = "SUB/BTC"
    min_trigger_market = "ADA/BNB"

    # order from neutral state => true
    assert await consumer.can_create_order(symbol, octobot_trading.enums.EvaluatorStates.NEUTRAL.value)

    # sell order using a currency with 0 available
    assert not await consumer.can_create_order(not_owned_symbol, octobot_trading.enums.EvaluatorStates.SHORT.value)
    assert not await consumer.can_create_order(not_owned_symbol, octobot_trading.enums.EvaluatorStates.VERY_SHORT.value)

    # sell order using a currency with < min available
    assert not await consumer.can_create_order(min_trigger_symbol, octobot_trading.enums.EvaluatorStates.SHORT.value)
    assert not await consumer.can_create_order(min_trigger_symbol, octobot_trading.enums.EvaluatorStates.VERY_SHORT.value)

    # sell order using a currency with > min available
    assert await consumer.can_create_order(not_owned_market, octobot_trading.enums.EvaluatorStates.SHORT.value)
    assert await consumer.can_create_order(not_owned_market, octobot_trading.enums.EvaluatorStates.VERY_SHORT.value)

    # buy order using a market with 0 available
    assert not await consumer.can_create_order(not_owned_market, octobot_trading.enums.EvaluatorStates.LONG.value)
    assert not await consumer.can_create_order(not_owned_market, octobot_trading.enums.EvaluatorStates.VERY_LONG.value)

    # buy order using a market with < min available
    assert not await consumer.can_create_order(min_trigger_market, octobot_trading.enums.EvaluatorStates.LONG.value)
    assert not await consumer.can_create_order(min_trigger_market, octobot_trading.enums.EvaluatorStates.VERY_LONG.value)

    # buy order using a market with > min available
    assert await consumer.can_create_order(not_owned_symbol, octobot_trading.enums.EvaluatorStates.LONG.value)
    assert await consumer.can_create_order(not_owned_symbol, octobot_trading.enums.EvaluatorStates.VERY_LONG.value)


async def test_can_create_order_unknown_symbols():
    _, _, consumer = await _get_tools()
    unknown_symbol = "VI?/BTC"
    unknown_market = "BTC/*s?"
    unknown_everything = "VI?/*s?"

    # buy order with unknown market
    assert not await consumer.can_create_order(unknown_market, octobot_trading.enums.EvaluatorStates.LONG.value)
    assert not await consumer.can_create_order(unknown_market, octobot_trading.enums.EvaluatorStates.VERY_LONG.value)
    assert await consumer.can_create_order(unknown_market, octobot_trading.enums.EvaluatorStates.SHORT.value)
    assert await consumer.can_create_order(unknown_market, octobot_trading.enums.EvaluatorStates.VERY_SHORT.value)

    # sell order with unknown symbol
    assert not await consumer.can_create_order(unknown_symbol, octobot_trading.enums.EvaluatorStates.SHORT.value)
    assert not await consumer.can_create_order(unknown_symbol, octobot_trading.enums.EvaluatorStates.VERY_SHORT.value)
    assert await consumer.can_create_order(unknown_symbol, octobot_trading.enums.EvaluatorStates.LONG.value)
    assert await consumer.can_create_order(unknown_symbol, octobot_trading.enums.EvaluatorStates.VERY_LONG.value)

    # neutral state with unknown symbol, market and everything
    assert await consumer.can_create_order(unknown_symbol, octobot_trading.enums.EvaluatorStates.NEUTRAL.value)
    assert await consumer.can_create_order(unknown_market, octobot_trading.enums.EvaluatorStates.NEUTRAL.value)
    assert await consumer.can_create_order(unknown_everything,  octobot_trading.enums.EvaluatorStates.NEUTRAL.value)


async def test_valid_create_new_order():
    _, symbol, consumer = await _get_tools()

    # should raise NotImplementedError Exception
    with pytest.raises(NotImplementedError):
        await consumer.create_new_orders(symbol, -1, octobot_trading.enums.EvaluatorStates.NEUTRAL)
    with pytest.raises(NotImplementedError):
        await consumer.create_new_orders(symbol, -1, octobot_trading.enums.EvaluatorStates.VERY_SHORT, xyz=1)
    with pytest.raises(NotImplementedError):
        await consumer.create_new_orders(symbol, -1, octobot_trading.enums.EvaluatorStates.LONG, xyz=1, aaa="bbb")


async def test_get_number_of_traded_assets():
    exchange_manager, symbol, consumer = await _get_tools()
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.\
        origin_crypto_currencies_values = {
            symbol: 1,
            "xyz": 2,
            "aaa": 3
        }
    assert consumer.get_number_of_traded_assets() == 3


async def test_update_producer_last_activity():
    exchange_manager, symbol, consumer = await _get_tools()
    mode = consumer.trading_mode
    producer = AbstractTradingModeProducer(
        mock.Mock(exchange_manager=exchange_manager), exchange_manager.config, mode, exchange_manager
    )
    mode.producers.append(producer)
    assert producer.last_activity == TradingModeActivity()
    consumer._update_producer_last_activity(octobot_trading.enums.TradingModeActivityType.NOTHING_TO_DO, "plop")
    assert producer.last_activity == TradingModeActivity(
        octobot_trading.enums.TradingModeActivityType.NOTHING_TO_DO, {TRADING_MODE_ACTIVITY_REASON: "plop"}
    )
    consumer._update_producer_last_activity(octobot_trading.enums.TradingModeActivityType.CREATED_ORDERS, "11")
    assert producer.last_activity == TradingModeActivity(
        octobot_trading.enums.TradingModeActivityType.CREATED_ORDERS, {TRADING_MODE_ACTIVITY_REASON: "11"}
    )


async def test_create_order_if_possible_ensure_no_deadlock_when_canceling_orders():
    exchange_manager, symbol, consumer = await _get_tools()
    with mock.patch.object(
        exchange_manager.exchange, "get_exchange_current_time", mock.Mock(return_value=time.time())
    ):
        # 1. simple case: no concurrent task
        open_order = await _create_initialized_open_order(exchange_manager, symbol)
        async def _create_new_orders(*_, **__):
            # order is successfully canceled
            cancelled, _ = await consumer.trading_mode.cancel_order(open_order, wait_for_cancelling=True)
            assert cancelled is True

        assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == [open_order]
        with mock.patch.object(consumer, "create_new_orders", mock.AsyncMock(side_effect=_create_new_orders)) as _create_new_orders_mock:
            await consumer.create_order_if_possible(symbol, -1, octobot_trading.enums.EvaluatorStates.VERY_LONG.value)
            _create_new_orders_mock.assert_called_once_with(symbol, -1, octobot_trading.enums.EvaluatorStates.VERY_LONG.value)
            # ensure no error was raised
            assert symbol not in consumer.previous_call_error_per_symbol
        assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == []   # order no more open

        # 2. concurrent task: open_order is being filled BEFORE create_order_if_possible is called
        #   => create_order_if_possible will wait until order releases portfolio lock (and therefore is completely filled)
        #   before calling _create_new_orders
        open_order = await _create_initialized_open_order(exchange_manager, symbol)

        async def _delayed_handle_portfolio_and_position_update_from_order(*args, **kwargs):
            # force taking a long time to process handle_portfolio_and_position_update_from_order
            # so that the other task has to wait
            _origin_handle_portfolio_and_position_update_from_order_calls.append(1)
            for _ in range(50):
                await asyncio_tools.wait_asyncio_next_cycle()
            await origin_handle_portfolio_and_position_update_from_order(*args, **kwargs)
            _origin_handle_portfolio_and_position_update_from_order_calls.append(1)

        async def _filling_order_task():
            for _ in range(4):
                # let _create_new_orders be called
                await asyncio_tools.wait_asyncio_next_cycle()
            await open_order.on_fill()
            handle_portfolio_and_position_update_from_order_mock.assert_called_once()

        async def _create_order_if_possible_task():
            for _ in range(8):
                # let _delayed_handle_portfolio_and_position_update_from_order be called
                await asyncio_tools.wait_asyncio_next_cycle()
            assert _origin_handle_portfolio_and_position_update_from_order_calls == [1]
            await consumer.create_order_if_possible(symbol, -1, octobot_trading.enums.EvaluatorStates.VERY_LONG.value)

        async def _create_new_orders(*_, **__):
            # _delayed_handle_portfolio_and_position_update_from_order already completed before this is called
            assert _origin_handle_portfolio_and_position_update_from_order_calls == [1, 1]
            assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == []   # order no more open
            # order is not canceled: it's not in open orders anymore by the time _create_new_orders is called
            cancelled, _ = await consumer.trading_mode.cancel_order(open_order, wait_for_cancelling=True)
            assert cancelled is False  # assert error not propagated #raise

        _origin_handle_portfolio_and_position_update_from_order_calls = []
        origin_handle_portfolio_and_position_update_from_order = exchange_manager.exchange_personal_data.handle_portfolio_and_position_update_from_order
        assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == [open_order]
        with mock.patch.object(
            consumer, "create_new_orders", mock.AsyncMock(side_effect=_create_new_orders)
        ) as _create_new_orders_mock, \
        mock.patch.object(
            exchange_manager.exchange_personal_data, "handle_portfolio_and_position_update_from_order",
            mock.AsyncMock(side_effect=_delayed_handle_portfolio_and_position_update_from_order)
        ) as handle_portfolio_and_position_update_from_order_mock:
            await asyncio.gather(_filling_order_task(), _create_order_if_possible_task())
            _create_new_orders_mock.assert_called_once_with(symbol, -1, octobot_trading.enums.EvaluatorStates.VERY_LONG.value)
            handle_portfolio_and_position_update_from_order_mock.assert_called_once()
            # ensure no error was raised
            assert symbol not in consumer.previous_call_error_per_symbol
            consumer.previous_call_error_per_symbol.clear()
        assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == []   # order no more open

        # 3. concurrent task: open_order is being filled AFTER create_order_if_possible is called
        #   => create_order_if_possible will take portfolio lock and not wait for fill order state terminate
        open_order = await _create_initialized_open_order(exchange_manager, symbol)
        exchange_manager.trader.simulate = False    # force exchange requests
        open_order.simulated = False    # force real order simulation
        assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == [open_order]
        completed_tasks = []
        timeout = 1 # 1s timeout

        async def _synchronize_with_exchange(*_, **__):
            _synchronize_with_exchange_calls.append(1)
            for _ in range(20):
                # wait for _create_new_orders to be called
                await asyncio_tools.wait_asyncio_next_cycle()
            open_order.state._force_final_state()
            _synchronize_with_exchange_calls.append(1)
            # on_refresh_successful will call _delayed_handle_portfolio_and_position_update_from_order
            asyncio.create_task(open_order.state.on_refresh_successful())


        async def _delayed_handle_portfolio_and_position_update_from_order(*args, **kwargs):
            # needs to wait for _create_new_orders to finish to release lock
            _origin_handle_portfolio_and_position_update_from_order_calls.append(1)
            await origin_handle_portfolio_and_position_update_from_order(*args, **kwargs)
            _origin_handle_portfolio_and_position_update_from_order_calls.append(1)

        async def _filling_order_task():
            event = asyncio.Event()
            completed_tasks.append(event)
            try:
                for _ in range(10):
                    # wait for _create_new_orders to be called
                    await asyncio_tools.wait_asyncio_next_cycle()
                await open_order.on_fill()
            finally:
                event.set()

        async def _create_order_if_possible_task():
            event = asyncio.Event()
            completed_tasks.append(event)
            try:
                assert _origin_handle_portfolio_and_position_update_from_order_calls == []
                await consumer.create_order_if_possible(symbol, -1, octobot_trading.enums.EvaluatorStates.VERY_LONG.value)
            finally:
                event.set()

        async def _create_new_orders(*_, **__):
            assert _origin_handle_portfolio_and_position_update_from_order_calls == []
            for _ in range(20):
                # let _filling_order_task be called
                # _synchronize_with_exchange is waiting
                await asyncio_tools.wait_asyncio_next_cycle()
            assert _synchronize_with_exchange_calls == [1]
            # _delayed_handle_portfolio_and_position_update_from_order is waiting for create_order_if_possible
            # to release portfolio lock
            assert _origin_handle_portfolio_and_position_update_from_order_calls == []
            # order is filling: still considered open
            assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == [open_order]
            assert open_order.status == octobot_trading.enums.OrderStatus.OPEN
            assert isinstance(open_order.state, personal_data.FillOrderState)
            assert open_order.state.state == octobot_trading.enums.States.REFRESHING  # state in refresh process
            # order cancel will fail: order is filled
            # will deadlock if waits for open_order.state transition
            with pytest.raises(octobot_trading.errors.FilledOrderError):
                await consumer.trading_mode.cancel_order(open_order, wait_for_cancelling=True)
            assert _origin_handle_portfolio_and_position_update_from_order_calls == []
            assert _synchronize_with_exchange_calls == [1]

        async def _timeout_task(timeout):
            for _ in range(5):
                # let completed_tasks be populated
                await asyncio_tools.wait_asyncio_next_cycle()
            try:
                await asyncio.wait_for(asyncio.gather(*[e.wait() for e in completed_tasks]), timeout)
            except asyncio.TimeoutError:
                raise AssertionError("Timed out: this means a deadlock is detected!")

        _origin_handle_portfolio_and_position_update_from_order_calls = []
        _synchronize_with_exchange_calls = []
        assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == [open_order]
        with mock.patch.object(
            consumer, "create_new_orders", mock.AsyncMock(side_effect=_create_new_orders)
        ) as _create_new_orders_mock, \
        mock.patch.object(
            exchange_manager.exchange_personal_data, "handle_portfolio_and_position_update_from_order",
            mock.AsyncMock(side_effect=_delayed_handle_portfolio_and_position_update_from_order)
        ) as handle_portfolio_and_position_update_from_order_mock, \
        mock.patch.object(
            personal_data.OrderState, "_synchronize_with_exchange", mock.AsyncMock(side_effect=_synchronize_with_exchange)
        ) as _synchronize_with_exchange_mock, \
        mock.patch.object(
            exchange_manager.exchange, "cancel_order", mock.AsyncMock(side_effect=octobot_trading.errors.OrderNotFoundOnCancelError)
        ) as cancel_order_mock:
            await asyncio.gather(_filling_order_task(), _create_order_if_possible_task(), _timeout_task(timeout))
            # at the end, _delayed_handle_portfolio_and_position_update_from_order has been completed
            assert _origin_handle_portfolio_and_position_update_from_order_calls == [1, 1]
            _create_new_orders_mock.assert_called_once_with(symbol, -1, octobot_trading.enums.EvaluatorStates.VERY_LONG.value)
            handle_portfolio_and_position_update_from_order_mock.assert_called_once()
            _synchronize_with_exchange_mock.assert_called_once()
            assert cancel_order_mock.call_count == 2    # called once and retried
            # ensure no error was raised
            assert symbol not in consumer.previous_call_error_per_symbol
            consumer.previous_call_error_per_symbol.clear()
        assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == []   # order no more open


        # 4. concurrent task: open_order is being canceled AFTER create_order_if_possible is called
        #   => create_order_if_possible will take portfolio lock and not wait for cancel order state terminate
        open_order = await _create_initialized_open_order(exchange_manager, symbol)
        open_order.simulated = False    # force real order simulation
        assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == [open_order]
        completed_tasks.clear()

        # re-use most of step 3 mocks

        async def _delayed_handle_portfolio_and_position_update_from_order(*args, **kwargs):
            # needs to wait for _create_new_orders to finish to release lock
            _origin_handle_portfolio_and_position_update_from_order_calls.append(1)
            await origin_handle_portfolio_and_position_update_from_order(*args, **kwargs)
            _origin_handle_portfolio_and_position_update_from_order_calls.append(1)

        async def _cancel_order_task():
            event = asyncio.Event()
            completed_tasks.append(event)
            for _ in range(10):
                # wait for _create_new_orders to be called
                await asyncio_tools.wait_asyncio_next_cycle()
            try:
                await open_order.on_cancel()
            finally:
                event.set()

        async def _create_new_orders(*_, **__):
            assert _origin_handle_portfolio_and_position_update_from_order_calls == []
            for _ in range(20):
                # let _filling_order_task be called
                # _synchronize_with_exchange is waiting
                await asyncio_tools.wait_asyncio_next_cycle()
            assert _synchronize_with_exchange_calls == [1]
            # _delayed_handle_portfolio_and_position_update_from_order is waiting for create_order_if_possible
            # to release portfolio lock
            assert _origin_handle_portfolio_and_position_update_from_order_calls == []
            # order is filling: still considered open
            assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == [open_order]
            assert open_order.status == octobot_trading.enums.OrderStatus.OPEN
            assert isinstance(open_order.state, personal_data.CancelOrderState)
            assert open_order.state.state == octobot_trading.enums.States.REFRESHING  # state in refresh process
            # order cancel will succeed: order is already canceled
            # will deadlock if waits for open_order.state transition
            cancelled, _ = await consumer.trading_mode.cancel_order(open_order, wait_for_cancelling=True)
            assert cancelled is True
            assert _origin_handle_portfolio_and_position_update_from_order_calls == []
            assert _synchronize_with_exchange_calls == [1]

        _origin_handle_portfolio_and_position_update_from_order_calls = []
        _synchronize_with_exchange_calls = []
        assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == [open_order]
        with mock.patch.object(
            consumer, "create_new_orders", mock.AsyncMock(side_effect=_create_new_orders)
        ) as _create_new_orders_mock, \
        mock.patch.object(
            exchange_manager.exchange_personal_data, "handle_portfolio_and_position_update_from_order",
            mock.AsyncMock(side_effect=_delayed_handle_portfolio_and_position_update_from_order)
        ) as handle_portfolio_and_position_update_from_order_mock, \
        mock.patch.object(
            personal_data.CancelOrderState, "_synchronize_with_exchange", mock.AsyncMock(side_effect=_synchronize_with_exchange)
        ) as _synchronize_with_exchange_mock, \
        mock.patch.object(
            exchange_manager.exchange, "cancel_order", mock.AsyncMock(side_effect=octobot_trading.errors.OrderNotFoundOnCancelError)
        ) as cancel_order_mock:
            await asyncio.gather(_cancel_order_task(), _create_order_if_possible_task(), _timeout_task(timeout))
            # at the end, _delayed_handle_portfolio_and_position_update_from_order has been completed
            assert _origin_handle_portfolio_and_position_update_from_order_calls == [1, 1]
            _create_new_orders_mock.assert_called_once_with(symbol, -1, octobot_trading.enums.EvaluatorStates.VERY_LONG.value)
            handle_portfolio_and_position_update_from_order_mock.assert_called_once()
            _synchronize_with_exchange_mock.assert_called_once()
            assert cancel_order_mock.call_count == 2    # called once and retried
            # ensure no error was raised
            assert symbol not in consumer.previous_call_error_per_symbol
            consumer.previous_call_error_per_symbol.clear()
        assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == []   # order no more open


        # 5. no concurrent task: open_order ends up in PENDING_CANCEL state after exchange.cancel() call
        #   order.on_cancel() and don't dead lock in cancelled order state
        #   => create_order_if_possible (which has portfolio lock) will not wait for cancel order state terminate
        open_order = await _create_initialized_open_order(exchange_manager, symbol)
        open_order.simulated = False    # force real order simulation
        assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == [open_order]
        completed_tasks.clear()

        async def _synchronize_with_exchange(*_, **__):
            # will not set order in final state => don't do anything, order stays pending
            _synchronize_with_exchange_calls.append(1)
            _synchronize_with_exchange_calls.append(1)

        async def _create_new_orders(*_, **__):
            # for now order is open
            assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == [open_order]
            assert open_order.status == octobot_trading.enums.OrderStatus.OPEN
            assert isinstance(open_order.state, personal_data.OpenOrderState)
            # order cancel will end up in PENDING_CANCEL
            cancelled, _ = await consumer.trading_mode.cancel_order(open_order, wait_for_cancelling=True)
            cancelled is True
            # order now in pending cancel state
            assert isinstance(open_order.state, personal_data.CancelOrderState)
            assert open_order.is_pending_cancel_state() is True
            for _ in range(10):
                # wait a few cycles to make sure handle_portfolio_and_position_update_from_order_calls
                # really don't get called (locked by consumer lock
                await asyncio_tools.wait_asyncio_next_cycle()
            # _synchronize_with_exchange_calls started and completed
            assert _synchronize_with_exchange_calls == [1, 1]

        async def _on_cancel(*args, **kwargs):
            await origin_on_cancel(*args, **kwargs)


        _synchronize_with_exchange_calls = []
        _origin_handle_portfolio_and_position_update_from_order_calls = []
        origin_on_cancel = open_order.on_cancel
        assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == [open_order]
        with mock.patch.object(
            consumer, "create_new_orders", mock.AsyncMock(side_effect=_create_new_orders)
        ) as _create_new_orders_mock, mock.patch.object(
            open_order, "on_cancel", mock.AsyncMock(side_effect=_on_cancel)
        ) as _on_cancel_mock, \
        mock.patch.object(
            exchange_manager.exchange_personal_data, "handle_portfolio_and_position_update_from_order", mock.AsyncMock()
        ) as handle_portfolio_and_position_update_from_order_mock, \
        mock.patch.object(
            personal_data.CancelOrderState, "_synchronize_with_exchange", mock.AsyncMock(side_effect=_synchronize_with_exchange)
        ) as _synchronize_with_exchange_mock, \
        mock.patch.object(
            exchange_manager.exchange, "cancel_order", mock.AsyncMock(return_value=octobot_trading.enums.OrderStatus.PENDING_CANCEL)
        ) as cancel_order_mock:
            # doesn't create a concurrent cancel order task let, it will be created from then on_cancel() call
            await asyncio.gather(_create_order_if_possible_task(), _timeout_task(timeout))
            _create_new_orders_mock.assert_called_once_with(symbol, -1, octobot_trading.enums.EvaluatorStates.VERY_LONG.value)
            cancel_order_mock.assert_called_once()
            _on_cancel_mock.assert_called_once()
            handle_portfolio_and_position_update_from_order_mock.assert_not_called()    # call has been skipped for the test
            _synchronize_with_exchange_mock.assert_called_once()
            # ensure no error was raised
            assert symbol not in consumer.previous_call_error_per_symbol
            consumer.previous_call_error_per_symbol.clear()
        assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == []   # order no more open


        # 6. concurrent task: open_order ends up in PENDING_CANCEL state after exchange.cancel() call
        #   because order is already refreshing (ex: from open orders updater)
        #   => create_order_if_possible (which has portfolio lock) will not wait for cancel order state terminate
        open_order = await _create_initialized_open_order(exchange_manager, symbol)
        open_order.simulated = False    # force real order simulation
        assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == [open_order]
        completed_tasks.clear()

        async def _synchronize_with_exchange(*_, **__):
            # will not set order in final state => don't do anything, order stays pending
            _synchronize_with_exchange_calls.append(1)
            for _ in range(10):
                # wait a few cycles to let _cancel_order trading_mode.cancel_order
                await asyncio_tools.wait_asyncio_next_cycle()
            _synchronize_with_exchange_calls.append(1)

        async def _create_new_orders(*_, **__):
            assert _origin_handle_portfolio_and_position_update_from_order_calls == []
            # for now order is open
            assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == [open_order]
            assert open_order.status == octobot_trading.enums.OrderStatus.OPEN
            assert isinstance(open_order.state, personal_data.OpenOrderState)
            # order cancel will end up in PENDING_CANCEL
            cancelled, _ = await consumer.trading_mode.cancel_order(open_order, wait_for_cancelling=True)
            assert cancelled is True
            # _synchronize_with_exchange_calls is still waiting
            assert _synchronize_with_exchange_calls == [1]
            assert open_order.is_refreshing() is True
            # order now in pending cancel state
            assert isinstance(open_order.state, personal_data.CancelOrderState)
            assert open_order.is_refreshing_canceling_state() is True
            for _ in range(10):
                # wait a few cycles to make sure _origin_handle_portfolio_and_position_update_from_order_calls
                # really don't get called (locked by consumer lock
                await asyncio_tools.wait_asyncio_next_cycle()
            # _delayed_handle_portfolio_and_position_update_from_order is waiting for consumer to release lock
            assert _origin_handle_portfolio_and_position_update_from_order_calls == []
            # _synchronize_with_exchange_calls is now completed
            assert _synchronize_with_exchange_calls == [1, 1]

        async def _on_cancel(*args, **kwargs):
            await origin_on_cancel(*args, **kwargs)

        async def _cancel_order(*args, **kwargs):
            # simulate an on_cancel call from somewhere else => triggers a canceling state
            open_order.status = octobot_trading.enums.OrderStatus.PENDING_CANCEL
            asyncio.create_task(open_order.on_cancel()) # will leave order in refreshing
            await asyncio_tools.wait_asyncio_next_cycle()   # let task run once (trigger refreshing state)
            return octobot_trading.enums.OrderStatus.PENDING_CANCEL

        _origin_handle_portfolio_and_position_update_from_order_calls = []
        _synchronize_with_exchange_calls = []
        origin_on_cancel = open_order.on_cancel
        origin_ensure_probably_canceled_order = exchange_manager.trader._ensure_probably_canceled_order
        assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == [open_order]
        with mock.patch.object(
            consumer, "create_new_orders", mock.AsyncMock(side_effect=_create_new_orders)
        ) as _create_new_orders_mock, mock.patch.object(
            open_order, "on_cancel", mock.AsyncMock(side_effect=_on_cancel)
        ) as _on_cancel_mock, \
        mock.patch.object(
            exchange_manager.exchange_personal_data, "handle_portfolio_and_position_update_from_order", mock.AsyncMock()
        ) as handle_portfolio_and_position_update_from_order_mock, \
        mock.patch.object(
            personal_data.CancelOrderState, "_synchronize_with_exchange", mock.AsyncMock(side_effect=_synchronize_with_exchange)
        ) as _synchronize_with_exchange_mock, \
        mock.patch.object(
            exchange_manager.exchange, "cancel_order", mock.AsyncMock(side_effect=_cancel_order)
        ) as cancel_order_mock, \
        mock.patch.object(
            exchange_manager.trader, "_ensure_probably_canceled_order", mock.AsyncMock(side_effect=origin_ensure_probably_canceled_order)
        ) as _ensure_probably_canceled_order_mock:
            # doesn't create a concurrent cancel order task let, it will be created from then on_cancel() call
            await asyncio.gather(_create_order_if_possible_task(), _timeout_task(timeout))
            _create_new_orders_mock.assert_called_once_with(symbol, -1, octobot_trading.enums.EvaluatorStates.VERY_LONG.value)
            cancel_order_mock.assert_called_once()
            _on_cancel_mock.assert_called_once()
            handle_portfolio_and_position_update_from_order_mock.assert_not_called()    # call has been skipped for the test
            _synchronize_with_exchange_mock.assert_called_once()
            _ensure_probably_canceled_order_mock.assert_called_once()
            # ensure no error was raised
            assert symbol not in consumer.previous_call_error_per_symbol
            consumer.previous_call_error_per_symbol.clear()
        assert exchange_manager.exchange_personal_data.orders_manager.get_open_orders() == []   # order no more open


async def _create_initialized_open_order(exchange_manager, symbol):
    open_order = personal_data.BuyLimitOrder(exchange_manager.trader)
    open_order.update(order_type=octobot_trading.enums.TraderOrderType.BUY_LIMIT,
                      symbol=symbol,
                      current_price=decimal.Decimal("70"),
                      quantity=decimal.Decimal("2"),
                      price=decimal.Decimal("70"))

    await open_order.initialize()
    await exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(open_order)
    return open_order
