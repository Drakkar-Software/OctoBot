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
import pytest
import mock
import decimal

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import tentacles.Trading.Mode.arbitrage_trading_mode.arbitrage_container as arbitrage_container_import
import tentacles.Trading.Mode.arbitrage_trading_mode.arbitrage_trading as arbitrage_trading_mode
import tentacles.Trading.Mode.arbitrage_trading_mode.tests as arbitrage_trading_mode_tests
import octobot_tentacles_manager.api as tentacles_manager_api

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_init():
    tentacles_manager_api.reload_tentacle_info()
    async with arbitrage_trading_mode_tests.exchange("binance") as arbitrage_trading_mode_tests.exchange_tuple:
        binance_producer, binance_consumer, _ = arbitrage_trading_mode_tests.exchange_tuple

        # trading mode
        assert len(binance_producer.trading_mode.consumers) == 2
        assert len(binance_producer.trading_mode.producers) == 1

        # consumer
        assert binance_consumer.PORTFOLIO_PERCENT_PER_TRADE > trading_constants.ZERO
        assert binance_consumer.STOP_LOSS_DELTA_FROM_OWN_PRICE > trading_constants.ZERO
        assert binance_consumer.open_arbitrages == []


async def test_create_new_orders():
    async with arbitrage_trading_mode_tests.exchange("binance") as arbitrage_trading_mode_tests.exchange_tuple:
        _, binance_consumer, _ = arbitrage_trading_mode_tests.exchange_tuple

        symbol = "BTC/USDT"
        final_note = None
        state = trading_enums.EvaluatorStates.SHORT
        with mock.patch.object(binance_consumer, "_create_initial_arbitrage_order",
                               new=mock.AsyncMock()) as initial_mock, \
                mock.patch.object(binance_consumer, "_create_secondary_arbitrage_order",
                                  new=mock.AsyncMock()) as secondary_mock:
            # no data in kwargs
            with pytest.raises(KeyError):
                await binance_consumer.create_new_orders(symbol, final_note, state)
            initial_mock.assert_not_called()
            secondary_mock.assert_not_called()

            data = {
                arbitrage_trading_mode.ArbitrageModeConsumer.ARBITRAGE_PHASE_KEY: arbitrage_trading_mode.ArbitrageModeConsumer.INITIAL_PHASE,
                arbitrage_trading_mode.ArbitrageModeConsumer.ARBITRAGE_CONTAINER_KEY: None
            }
            await binance_consumer.create_new_orders(symbol, final_note, state, data=data)
            initial_mock.assert_called_once()
            secondary_mock.assert_not_called()
            initial_mock.reset_mock()

            data = {
                arbitrage_trading_mode.ArbitrageModeConsumer.ARBITRAGE_PHASE_KEY: arbitrage_trading_mode.ArbitrageModeConsumer.SECONDARY_PHASE,
                arbitrage_trading_mode.ArbitrageModeConsumer.ARBITRAGE_CONTAINER_KEY: None,
                arbitrage_trading_mode.ArbitrageModeConsumer.QUANTITY_KEY: None
            }
            await binance_consumer.create_new_orders(symbol, final_note, state, data=data)
            initial_mock.assert_not_called()
            secondary_mock.assert_called_once()


async def test_create_initial_arbitrage_order():
    async with arbitrage_trading_mode_tests.exchange("binance") as arbitrage_trading_mode_tests.exchange_tuple:
        _, binance_consumer, _ = arbitrage_trading_mode_tests.exchange_tuple
        price = decimal.Decimal(10)
        # long
        arbitrage = arbitrage_container_import.ArbitrageContainer(price, decimal.Decimal(15), trading_enums.EvaluatorStates.LONG)
        orders = await binance_consumer._create_initial_arbitrage_order(arbitrage)
        assert orders
        order = orders[0]
        assert order.exchange_order_type is trading_enums.TradeOrderType.LIMIT
        assert order.order_type is trading_enums.TraderOrderType.BUY_LIMIT
        assert order.side is trading_enums.TradeOrderSide.BUY
        assert order.symbol == binance_consumer.trading_mode.symbol
        assert order.order_id == arbitrage.initial_limit_order_id
        assert arbitrage in binance_consumer.open_arbitrages

        # short
        arbitrage = arbitrage_container_import.ArbitrageContainer(price, decimal.Decimal(15), trading_enums.EvaluatorStates.SHORT)
        orders = await binance_consumer._create_initial_arbitrage_order(arbitrage)
        assert orders
        order = orders[0]
        assert order.exchange_order_type is trading_enums.TradeOrderType.LIMIT
        assert order.order_type is trading_enums.TraderOrderType.SELL_LIMIT
        assert order.side is trading_enums.TradeOrderSide.SELL
        assert order.symbol == binance_consumer.trading_mode.symbol
        assert order.order_id == arbitrage.initial_limit_order_id
        assert arbitrage in binance_consumer.open_arbitrages


async def test_create_secondary_arbitrage_order():
    async with arbitrage_trading_mode_tests.exchange("binance") as arbitrage_trading_mode_tests.exchange_tuple:
        _, binance_consumer, exchange_manager = arbitrage_trading_mode_tests.exchange_tuple
        price = decimal.Decimal(10)

        # disable inactive orders
        exchange_manager.trader.enable_inactive_orders = False
        # long
        arbitrage = arbitrage_container_import.ArbitrageContainer(
            price, decimal.Decimal(15), trading_enums.EvaluatorStates.LONG
        )
        quantity = decimal.Decimal(5)
        orders = await binance_consumer._create_secondary_arbitrage_order(arbitrage, quantity)
        assert orders

        limit_order = orders[0]
        assert limit_order.exchange_order_type is trading_enums.TradeOrderType.LIMIT
        assert limit_order.order_type is trading_enums.TraderOrderType.SELL_LIMIT
        assert limit_order.side is trading_enums.TradeOrderSide.SELL
        assert limit_order.symbol == binance_consumer.trading_mode.symbol
        assert limit_order.order_id == arbitrage.secondary_limit_order_id
        assert limit_order.origin_quantity == quantity
        assert limit_order.associated_entry_ids is None
        assert limit_order.is_active is True

        order_group_1 = limit_order.order_group
        stop_order = order_group_1.get_group_open_orders()[1]
        assert order_group_1 is stop_order.order_group
        assert stop_order.exchange_order_type is trading_enums.TradeOrderType.STOP_LOSS
        assert stop_order.order_type is trading_enums.TraderOrderType.STOP_LOSS
        assert stop_order.side is trading_enums.TradeOrderSide.SELL
        assert stop_order.symbol == binance_consumer.trading_mode.symbol
        assert stop_order.order_id == arbitrage.secondary_stop_order_id
        assert stop_order.origin_quantity == quantity
        assert stop_order.is_active is True
        assert limit_order.associated_entry_ids is None

        # enable inactive orders
        exchange_manager.trader.enable_inactive_orders = True

        # short
        arbitrage = arbitrage_container_import.ArbitrageContainer(
            price, decimal.Decimal(15), trading_enums.EvaluatorStates.SHORT
        )
        arbitrage.initial_limit_order_id = "123"
        quantity = decimal.Decimal(5)
        orders = await binance_consumer._create_secondary_arbitrage_order(arbitrage, quantity)
        assert orders

        limit_order = orders[0]
        assert limit_order.exchange_order_type is trading_enums.TradeOrderType.LIMIT
        assert limit_order.order_type is trading_enums.TraderOrderType.BUY_LIMIT
        assert limit_order.side is trading_enums.TradeOrderSide.BUY
        assert limit_order.symbol == binance_consumer.trading_mode.symbol
        assert limit_order.order_id == arbitrage.secondary_limit_order_id
        assert limit_order.origin_quantity == quantity
        assert limit_order.is_active is False
        assert limit_order.associated_entry_ids == ["123"]

        order_group_2 = limit_order.order_group
        stop_order = order_group_2.get_group_open_orders()[1]
        assert order_group_2 is stop_order.order_group
        assert order_group_2 != order_group_1
        assert stop_order.exchange_order_type is trading_enums.TradeOrderType.STOP_LOSS
        assert stop_order.order_type is trading_enums.TraderOrderType.STOP_LOSS
        assert stop_order.side is trading_enums.TradeOrderSide.BUY
        assert stop_order.symbol == binance_consumer.trading_mode.symbol
        assert stop_order.order_id == arbitrage.secondary_stop_order_id
        assert stop_order.origin_quantity == quantity
        assert stop_order.is_active is True
        assert limit_order.associated_entry_ids == ["123"]


async def test_get_quantity_from_holdings():
    async with arbitrage_trading_mode_tests.exchange("binance") as arbitrage_trading_mode_tests.exchange_tuple:
        _, binance_consumer, _ = arbitrage_trading_mode_tests.exchange_tuple
        binance_consumer.PORTFOLIO_PERCENT_PER_TRADE = decimal.Decimal(str(0.5))
        assert binance_consumer._get_quantity_from_holdings(decimal.Decimal(str(10)), decimal.Decimal(str(100)), trading_enums.EvaluatorStates.SHORT) == decimal.Decimal(str(5))
        assert binance_consumer._get_quantity_from_holdings(decimal.Decimal(str(10)), decimal.Decimal(str(100)), trading_enums.EvaluatorStates.LONG) == decimal.Decimal(str(50))


async def test_get_stop_loss_price():
    async with arbitrage_trading_mode_tests.exchange("binance") as arbitrage_trading_mode_tests.exchange_tuple:
        _, binance_consumer, arbitrage_trading_mode_tests.exchange_manager = arbitrage_trading_mode_tests.exchange_tuple
        binance_consumer.STOP_LOSS_DELTA_FROM_OWN_PRICE = decimal.Decimal(str(0.01))
        symbol_market = arbitrage_trading_mode_tests.exchange_manager.exchange.get_market_status("BTC/USDT",
                                                                                                 with_fixer=False)
        assert binance_consumer._get_stop_loss_price(symbol_market, decimal.Decimal(str(100)), True) == decimal.Decimal(str(99))
        assert binance_consumer._get_stop_loss_price(symbol_market, decimal.Decimal(str(100)), False) == decimal.Decimal(str(101))
