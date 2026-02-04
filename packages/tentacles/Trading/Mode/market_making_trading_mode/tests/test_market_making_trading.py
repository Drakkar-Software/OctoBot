# Drakkar-Software OctoBot-Tentacles
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
import contextlib
import mock
import os
import pytest


import async_channel.util as channel_util
import octobot_commons.constants as commons_constants
import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.tests.test_config as test_config
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_backtesting.api as backtesting_api
import octobot_trading.api as trading_api
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as exchanges
import tentacles.Trading.Mode.market_making_trading_mode.market_making_trading as market_making_trading

import tests.test_utils.config as test_utils_config
import tests.test_utils.test_exchanges as test_exchanges
import tests.test_utils.trading_modes as test_trading_modes

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

# binance symbol market extract
SYMBOL_MARKET = {
    'id': 'BTCUSDT', 'lowercaseId': 'btcusdt', 'symbol': 'BTC/USDT', 'base': 'BTC', 'quote': 'USDT',
    'settle': None, 'baseId': 'BTC', 'quoteId': 'USDT', 'settleId': None, 'type': 'spot', 'spot': True,
    'margin': True, 'swap': False, 'future': False, 'option': False, 'index': None, 'active': True,
    'contract': False, 'linear': None, 'inverse': None, 'subType': None, 'taker': 0.001, 'maker': 0.001,
    'contractSize': None, 'expiry': None, 'expiryDatetime': None, 'strike': None, 'optionType': None,
    'precision': {'amount': 5, 'price': 2, 'cost': None, 'base': 1e-08, 'quote': 1e-08},
    'limits': {
        'leverage': {'min': None, 'max': None},
        'amount': {'min': 1e-05, 'max': 9000.0},
        'price': {'min': 0.01, 'max': 1000000.0},
        'cost': {'min': 5.0, 'max': 9000000.0},
        'market': {'min': 0.0, 'max': 107.1489592}
    }, 'created': None,
    'percentage': True, 'feeSide': 'get', 'tierBased': False
}

def _get_mm_config():
    return {
      "asks_count": 5,
      "bids_count": 5,
      "min_spread": 5,
      "max_spread": 20,
      "reference_exchange": "local",
    }


async def _init_trading_mode(config, exchange_manager, symbol):
    mode = market_making_trading.MarketMakingTradingMode(config, exchange_manager)
    mode.symbol = None if mode.get_is_symbol_wildcard() else symbol
    mode.trading_config = _get_mm_config()
    await mode.initialize(trading_config=mode.trading_config)
    # add mode to exchange manager so that it can be stopped and freed from memory
    exchange_manager.trading_modes.append(mode)
    test_trading_modes.set_ready_to_start(mode.producers[0])
    return mode, mode.producers[0]


@contextlib.asynccontextmanager
async def _get_tools(symbol, additional_portfolio={}):
    tentacles_manager_api.reload_tentacle_info()
    exchange_manager = None
    try:
        config = test_config.load_test_config()
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]["USDT"] = 1000
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO][
            "BTC"] = 10
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO].update(additional_portfolio)
        exchange_manager = test_exchanges.get_test_exchange_manager(config, "binance")
        exchange_manager.tentacles_setup_config = test_utils_config.load_test_tentacles_config()

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

        # set BTC/USDT price at 1000 USDT
        if symbol not in exchange_manager.client_symbols:
            exchange_manager.client_symbols.append(symbol)
        trading_api.force_set_mark_price(exchange_manager, symbol, 1000)

        mode, producer = await _init_trading_mode(config, exchange_manager, symbol)

        yield producer, mode.get_trading_mode_consumers()[0], exchange_manager
    finally:
        if exchange_manager:
            await _stop(exchange_manager)


async def _stop(exchange_manager):
    for importer in backtesting_api.get_importers(exchange_manager.exchange.backtesting):
        await backtesting_api.stop_importer(importer)
    await exchange_manager.exchange.backtesting.stop()
    await exchange_manager.stop()


async def test_handle_market_making_orders_from_no_orders():
    symbol = "BTC/USDT"
    async with _get_tools(symbol) as (producer, consumer, exchange_manager):
        price = decimal.Decimal(1000)
        origin_submit_trading_evaluation = producer.submit_trading_evaluation
        with mock.patch.object(
            producer, "submit_trading_evaluation", mock.AsyncMock(side_effect=origin_submit_trading_evaluation)
        ) as submit_trading_evaluation_mock, mock.patch.object(
            producer, "_get_reference_price", mock.AsyncMock(return_value=price)
        ) as _get_reference_price_mock, mock.patch.object(
            producer, "_get_daily_volume", mock.Mock(return_value=(decimal.Decimal(1), decimal.Decimal(1000)))
        ) as _get_daily_volume_mock:
            trigger_source = "ref_price"
            # 1. full replace as no order exist
            assert await producer._handle_market_making_orders(price, SYMBOL_MARKET, trigger_source, False) is True
            _get_reference_price_mock.assert_called_once()
            _get_daily_volume_mock.assert_called_once()
            submit_trading_evaluation_mock.assert_called_once()
            assert submit_trading_evaluation_mock.mock_calls[0].kwargs["symbol"] == symbol
            data = submit_trading_evaluation_mock.mock_calls[0].kwargs["data"]
            assert data[market_making_trading.MarketMakingTradingModeConsumer.CURRENT_PRICE_KEY] == price
            assert data[market_making_trading.MarketMakingTradingModeConsumer.SYMBOL_MARKET_KEY] == SYMBOL_MARKET
            order_plan: market_making_trading.OrdersUpdatePlan = data[market_making_trading.MarketMakingTradingModeConsumer.ORDER_ACTIONS_PLAN_KEY]
            assert isinstance(order_plan, market_making_trading.OrdersUpdatePlan)
            assert len(order_plan.order_actions) == 10
            buy_actions = [
                a for a in order_plan.order_actions
                if isinstance(a, market_making_trading.CreateOrderAction)
                   and a.order_data.side == trading_enums.TradeOrderSide.BUY
            ]
            sell_actions = [
                a for a in order_plan.order_actions
                if isinstance(a, market_making_trading.CreateOrderAction)
                   and a.order_data.side == trading_enums.TradeOrderSide.SELL
            ]
            assert len(buy_actions) == len(sell_actions) == 5
            assert order_plan.cancelled == False
            assert order_plan.cancellable == False # full replace is not cancellable
            assert not order_plan.processed.is_set()
            assert order_plan.trigger_source == trigger_source

            # wait for orders to be created
            for _ in range(len(order_plan.order_actions)):
                await asyncio_tools.wait_asyncio_next_cycle()

            # ensure orders are properly created
            open_orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders(symbol)
            assert len(open_orders) == 10
            assert sorted([f"{o.origin_price}{o.side.value}" for o in open_orders]) == sorted([
                f"{a.order_data.price}{a.order_data.side.value}" for a in order_plan.order_actions
                if isinstance(a, market_making_trading.CreateOrderAction)
            ])
            _get_reference_price_mock.reset_mock()
            submit_trading_evaluation_mock.reset_mock()
            _get_daily_volume_mock.reset_mock()

            # 2. receive an update but orders are already in place: nothing to do
            assert await producer._handle_market_making_orders(price, SYMBOL_MARKET, trigger_source, False) is True
            _get_reference_price_mock.assert_called_once()
            submit_trading_evaluation_mock.assert_not_called()
            _get_reference_price_mock.reset_mock()
            _get_daily_volume_mock.reset_mock()

            # 3. receive an update, orders are already in place but force_full_refresh is True: refresh orders
            assert await producer._handle_market_making_orders(price, SYMBOL_MARKET, trigger_source, True) is True
            _get_reference_price_mock.assert_called_once()
            _get_daily_volume_mock.assert_called_once()
            submit_trading_evaluation_mock.assert_called_once()
            assert submit_trading_evaluation_mock.mock_calls[0].kwargs["symbol"] == symbol
            data = submit_trading_evaluation_mock.mock_calls[0].kwargs["data"]
            order_plan: market_making_trading.OrdersUpdatePlan = data[market_making_trading.MarketMakingTradingModeConsumer.ORDER_ACTIONS_PLAN_KEY]
            assert isinstance(order_plan, market_making_trading.OrdersUpdatePlan)
            assert len(order_plan.order_actions) == 20
            cancel_actions = [
                a for a in order_plan.order_actions
                if isinstance(a, market_making_trading.CancelOrderAction)
            ]
            buy_actions = [
                a for a in order_plan.order_actions
                if isinstance(a, market_making_trading.CreateOrderAction)
                   and a.order_data.side == trading_enums.TradeOrderSide.BUY
            ]
            sell_actions = [
                a for a in order_plan.order_actions
                if isinstance(a, market_making_trading.CreateOrderAction)
                   and a.order_data.side == trading_enums.TradeOrderSide.SELL
            ]
            assert len(cancel_actions) == 10
            assert len(buy_actions) == len(sell_actions) == 5
            assert order_plan.cancelled == False
            assert order_plan.cancellable == False # full replace is not cancellable
            assert not order_plan.processed.is_set()
            assert order_plan.trigger_source == trigger_source

            # wait for orders to be created
            for _ in range(len(order_plan.order_actions)):
                await asyncio_tools.wait_asyncio_next_cycle()

            # ensure orders are properly created
            open_orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders(symbol)
            assert len(open_orders) == 10
            assert sorted([f"{o.origin_price}{o.side.value}" for o in open_orders]) == sorted([
                f"{a.order_data.price}{a.order_data.side.value}" for a in order_plan.order_actions
                if isinstance(a, market_making_trading.CreateOrderAction)
            ])
            _get_reference_price_mock.reset_mock()
            submit_trading_evaluation_mock.reset_mock()


async def test_handle_market_making_orders_missing_funds_for_buy_orders():
    symbol = "BTC/USDT"
    async with _get_tools(symbol, additional_portfolio={"USDT": 15}) as (producer, consumer, exchange_manager):
        price = decimal.Decimal(1000)
        origin_submit_trading_evaluation = producer.submit_trading_evaluation
        with mock.patch.object(
            producer, "submit_trading_evaluation", mock.AsyncMock(side_effect=origin_submit_trading_evaluation)
        ) as submit_trading_evaluation_mock, mock.patch.object(
            producer, "_get_reference_price", mock.AsyncMock(return_value=price)
        ) as _get_reference_price_mock, mock.patch.object(
            producer, "_get_daily_volume", mock.Mock(return_value=(decimal.Decimal(1), decimal.Decimal(1000)))
        ) as _get_daily_volume_mock:
            trigger_source = "ref_price"
            # 1. full replace as no order exist
            assert await producer._handle_market_making_orders(price, SYMBOL_MARKET, trigger_source, False) is True
            _get_reference_price_mock.assert_called_once()
            _get_daily_volume_mock.assert_called_once()
            submit_trading_evaluation_mock.assert_called_once()
            data = submit_trading_evaluation_mock.mock_calls[0].kwargs["data"]
            order_plan: market_making_trading.OrdersUpdatePlan = data[market_making_trading.MarketMakingTradingModeConsumer.ORDER_ACTIONS_PLAN_KEY]
            assert len(order_plan.order_actions) == 10
            buy_actions = [
                a for a in order_plan.order_actions
                if isinstance(a, market_making_trading.CreateOrderAction)
                   and a.order_data.side == trading_enums.TradeOrderSide.BUY
            ]
            sell_actions = [
                a for a in order_plan.order_actions
                if isinstance(a, market_making_trading.CreateOrderAction)
                   and a.order_data.side == trading_enums.TradeOrderSide.SELL
            ]
            assert len(buy_actions) == len(sell_actions) == 5
            assert order_plan.cancellable == False # full replace is not cancellable

            # wait for orders to be created
            for _ in range(len(order_plan.order_actions)):
                await asyncio_tools.wait_asyncio_next_cycle()

            # ensure orders are properly created
            open_orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders(symbol)
            # # only sell orders are created
            assert sorted([f"{o.origin_price}{o.side.value}" for o in open_orders]) == sorted([
                f"{a.order_data.price}{a.order_data.side.value}" for a in sell_actions
            ])
            _get_reference_price_mock.reset_mock()
            submit_trading_evaluation_mock.reset_mock()

            # 2. receive an update but orders are already in place: nothing to do
            assert await producer._handle_market_making_orders(price, SYMBOL_MARKET, trigger_source, False) is True
            _get_reference_price_mock.assert_called_once()
            submit_trading_evaluation_mock.assert_not_called()
            _get_reference_price_mock.reset_mock()
            submit_trading_evaluation_mock.reset_mock()

            # 3. an order got cancelled: recreate book
            await exchange_manager.trader.cancel_order(open_orders[0])
            assert await producer._handle_market_making_orders(price, SYMBOL_MARKET, trigger_source, False) is True
            _get_reference_price_mock.assert_called_once()
            submit_trading_evaluation_mock.assert_called_once()
            data = submit_trading_evaluation_mock.mock_calls[0].kwargs["data"]
            order_plan: market_making_trading.OrdersUpdatePlan = data[market_making_trading.MarketMakingTradingModeConsumer.ORDER_ACTIONS_PLAN_KEY]
            assert len(order_plan.order_actions) == 9
            assert order_plan.cancellable == False # full replace is not cancellable
            buy_actions = [
                a for a in order_plan.order_actions
                if isinstance(a, market_making_trading.CreateOrderAction)
                   and a.order_data.side == trading_enums.TradeOrderSide.BUY
            ]
            assert not buy_actions
            sell_actions = [
                a for a in order_plan.order_actions
                if isinstance(a, market_making_trading.CreateOrderAction)
                   and a.order_data.side == trading_enums.TradeOrderSide.SELL
            ]
            assert len(sell_actions) == 5
            cancel_actions = [
                a for a in order_plan.order_actions
                if isinstance(a, market_making_trading.CancelOrderAction)
            ]
            assert sorted([a.order for a in cancel_actions], key=lambda x: x.origin_price) == (
                sorted(open_orders[1:], key=lambda x: x.origin_price)
            )

            # wait for orders to be cancelled and created
            for _ in range(len(order_plan.order_actions)):
                await asyncio_tools.wait_asyncio_next_cycle()

            # ensure orders are properly created
            open_orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders(symbol)
            # # only sell orders are created
            assert sorted([f"{o.origin_price}{o.side.value}" for o in open_orders]) == sorted([
                f"{a.order_data.price}{a.order_data.side.value}" for a in sell_actions
            ])
            _get_reference_price_mock.reset_mock()
            submit_trading_evaluation_mock.reset_mock()


async def test_register_on_reference_exchanges_if_required():
    symbol = "BTC/USDT"
    async with _get_tools(symbol) as (producer, consumer, exchange_manager):
        with mock.patch.object(
            producer, "_is_registered_on_all_reference_exchanges", mock.Mock()
        ) as is_registered_mock, mock.patch.object(
            producer, "_register_pair_requirement_on_reference_exchanges", mock.AsyncMock()
        ) as register_mock:
            # Test 1: Already registered - returns True immediately without calling register
            is_registered_mock.return_value = True
            result = await producer._register_on_reference_exchanges_if_required()
            assert result is True
            is_registered_mock.assert_called_once()
            register_mock.assert_not_called()

            is_registered_mock.reset_mock()

            # Test 2: Not registered, registration succeeds - calls register and returns True
            is_registered_mock.side_effect = [False, True]  # First call False, second call True
            result = await producer._register_on_reference_exchanges_if_required()
            assert result is True
            assert is_registered_mock.call_count == 2
            register_mock.assert_awaited_once()

            is_registered_mock.reset_mock()
            register_mock.reset_mock()

            # Test 3: Not registered, registration fails - calls register and returns False
            is_registered_mock.side_effect = [False, False]  # Both calls return False
            result = await producer._register_on_reference_exchanges_if_required()
            assert result is False
            assert is_registered_mock.call_count == 2
            register_mock.assert_awaited_once()
