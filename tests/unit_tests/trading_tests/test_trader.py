#  Drakkar-Software OctoBot
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

import ccxt
import copy
import pytest

from octobot_trading.exchanges import ExchangeManager
from config import *
from tests.test_utils.config import load_test_config
from trading.trader.order import *
from trading.trader.order_notifier import OrderNotifier
from trading.trader.trader import Trader
from trading.trader.trader_simulator import TraderSimulator
from trading.trader.portfolio import Portfolio


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestTrader:
    DEFAULT_SYMBOL = "BTC/USDT"

    @staticmethod
    async def init_default():
        config = load_test_config()
        exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
        await exchange_manager.initialize()
        exchange_inst = exchange_manager.get_exchange()
        trader_inst = TraderSimulator(config, exchange_inst, 2)
        await trader_inst.portfolio.initialize()
        return config, exchange_inst, trader_inst

    @staticmethod
    def stop(trader):
        trader.stop_order_manager()

    async def test_enabled(self):
        config, _, trader_inst = await self.init_default()
        self.stop(trader_inst)

        config[CONFIG_TRADER][CONFIG_ENABLED_OPTION] = True
        assert Trader.enabled(config)

        config[CONFIG_TRADER][CONFIG_ENABLED_OPTION] = False
        assert not Trader.enabled(config)

    async def test_get_risk(self):
        config, exchange_inst, trader_inst = await self.init_default()
        self.stop(trader_inst)

        config[CONFIG_TRADING][CONFIG_TRADER_RISK] = 0
        trader_1 = TraderSimulator(config, exchange_inst)
        assert trader_1.get_risk() == CONFIG_TRADER_RISK_MIN
        self.stop(trader_1)

        config[CONFIG_TRADING][CONFIG_TRADER_RISK] = 2
        trader_2 = TraderSimulator(config, exchange_inst)
        assert trader_2.get_risk() == CONFIG_TRADER_RISK_MAX
        self.stop(trader_2)

        config[CONFIG_TRADING][CONFIG_TRADER_RISK] = 0.5
        trader_2 = TraderSimulator(config, exchange_inst)
        assert trader_2.get_risk() == 0.5
        self.stop(trader_2)

    async def test_cancel_order(self):
        _, _, trader_inst = await self.init_default()

        # Test buy order
        market_buy = BuyMarketOrder(trader_inst)
        market_buy.new(TraderOrderType.BUY_MARKET,
                       self.DEFAULT_SYMBOL,
                       70,
                       10,
                       70)

        assert market_buy not in trader_inst.get_open_orders()

        trader_inst.get_order_manager().add_order_to_list(market_buy)

        assert market_buy in trader_inst.get_open_orders()

        await trader_inst.cancel_order(market_buy)

        assert market_buy not in trader_inst.get_open_orders()

        self.stop(trader_inst)

    async def test_cancel_open_orders_default_symbol(self):
        config, _, trader_inst = await self.init_default()

        # Test buy order
        market_buy = BuyMarketOrder(trader_inst)
        market_buy.new(TraderOrderType.BUY_MARKET,
                       self.DEFAULT_SYMBOL,
                       70,
                       10,
                       70)

        # Test sell order
        market_sell = SellMarketOrder(trader_inst)
        market_sell.new(TraderOrderType.SELL_MARKET,
                        self.DEFAULT_SYMBOL,
                        70,
                        10,
                        70)

        # Test buy order
        limit_buy = BuyLimitOrder(trader_inst)
        limit_buy.new(TraderOrderType.BUY_LIMIT,
                      self.DEFAULT_SYMBOL,
                      70,
                      10,
                      70)

        # create order notifier to prevent None call
        market_buy.order_notifier = OrderNotifier(config, market_buy)
        market_sell.order_notifier = OrderNotifier(config, market_sell)
        limit_buy.order_notifier = OrderNotifier(config, limit_buy)

        trader_inst.get_order_manager().add_order_to_list(market_buy)
        trader_inst.get_order_manager().add_order_to_list(market_sell)
        trader_inst.get_order_manager().add_order_to_list(limit_buy)

        assert market_buy in trader_inst.get_open_orders()
        assert market_sell in trader_inst.get_open_orders()
        assert limit_buy in trader_inst.get_open_orders()

        await trader_inst.cancel_open_orders(self.DEFAULT_SYMBOL)

        assert market_buy not in trader_inst.get_open_orders()
        assert market_sell not in trader_inst.get_open_orders()
        assert limit_buy not in trader_inst.get_open_orders()

        self.stop(trader_inst)

    async def test_cancel_open_orders_multi_symbol(self):
        config, _, trader_inst = await self.init_default()

        # Test buy order
        market_buy = BuyMarketOrder(trader_inst)
        market_buy.new(TraderOrderType.BUY_MARKET,
                       "BTC/EUR",
                       70,
                       10,
                       70)

        # Test buy order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(TraderOrderType.SELL_LIMIT,
                       "NANO/USDT",
                       70,
                       10,
                       70)

        # Test sell order
        market_sell = SellMarketOrder(trader_inst)
        market_sell.new(TraderOrderType.SELL_MARKET,
                        self.DEFAULT_SYMBOL,
                        70,
                        10,
                        70)

        # Test buy order
        limit_buy = BuyLimitOrder(trader_inst)
        limit_buy.new(TraderOrderType.BUY_LIMIT,
                      self.DEFAULT_SYMBOL,
                      70,
                      10,
                      70)

        # create order notifier to prevent None call
        market_buy.order_notifier = OrderNotifier(config, market_buy)
        market_sell.order_notifier = OrderNotifier(config, market_sell)
        limit_buy.order_notifier = OrderNotifier(config, limit_buy)
        limit_sell.order_notifier = OrderNotifier(config, limit_sell)

        trader_inst.get_order_manager().add_order_to_list(market_buy)
        trader_inst.get_order_manager().add_order_to_list(market_sell)
        trader_inst.get_order_manager().add_order_to_list(limit_buy)
        trader_inst.get_order_manager().add_order_to_list(limit_sell)

        assert market_buy in trader_inst.get_open_orders()
        assert market_sell in trader_inst.get_open_orders()
        assert limit_buy in trader_inst.get_open_orders()
        assert limit_sell in trader_inst.get_open_orders()

        await trader_inst.cancel_open_orders(self.DEFAULT_SYMBOL)

        assert market_buy in trader_inst.get_open_orders()
        assert market_sell not in trader_inst.get_open_orders()
        assert limit_buy not in trader_inst.get_open_orders()
        assert limit_sell in trader_inst.get_open_orders()

        self.stop(trader_inst)

    async def test_cancel_all_open_orders_with_currency(self):
        config, _, trader_inst = await self.init_default()

        # Test buy order
        market_buy = BuyMarketOrder(trader_inst)
        market_buy.new(TraderOrderType.BUY_MARKET,
                       "BTC/EUR",
                       70,
                       10,
                       70)

        # Test buy order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(TraderOrderType.SELL_LIMIT,
                       "XRB/BTC",
                       70,
                       10,
                       70)

        # Test sell order
        market_sell = SellMarketOrder(trader_inst)
        market_sell.new(TraderOrderType.SELL_MARKET,
                        self.DEFAULT_SYMBOL,
                        70,
                        10,
                        70)

        # Test buy order
        limit_buy = BuyLimitOrder(trader_inst)
        limit_buy.new(TraderOrderType.BUY_LIMIT,
                      self.DEFAULT_SYMBOL,
                      70,
                      10,
                      70)

        # create order notifier to prevent None call
        market_buy.order_notifier = OrderNotifier(config, market_buy)
        market_sell.order_notifier = OrderNotifier(config, market_sell)
        limit_buy.order_notifier = OrderNotifier(config, limit_buy)
        limit_sell.order_notifier = OrderNotifier(config, limit_sell)

        trader_inst.get_order_manager().add_order_to_list(market_buy)
        trader_inst.get_order_manager().add_order_to_list(market_sell)
        trader_inst.get_order_manager().add_order_to_list(limit_buy)
        trader_inst.get_order_manager().add_order_to_list(limit_sell)

        assert market_buy in trader_inst.get_open_orders()
        assert market_sell in trader_inst.get_open_orders()
        assert limit_buy in trader_inst.get_open_orders()
        assert limit_sell in trader_inst.get_open_orders()

        await trader_inst.cancel_all_open_orders_with_currency("XYZ")

        assert market_buy in trader_inst.get_open_orders()
        assert market_sell in trader_inst.get_open_orders()
        assert limit_buy in trader_inst.get_open_orders()
        assert limit_sell in trader_inst.get_open_orders()

        await trader_inst.cancel_all_open_orders_with_currency("XRB")

        assert market_buy in trader_inst.get_open_orders()
        assert market_sell in trader_inst.get_open_orders()
        assert limit_buy in trader_inst.get_open_orders()
        assert limit_sell not in trader_inst.get_open_orders()

        await trader_inst.cancel_all_open_orders_with_currency("USDT")

        assert market_buy in trader_inst.get_open_orders()
        assert market_sell not in trader_inst.get_open_orders()
        assert limit_buy not in trader_inst.get_open_orders()
        assert limit_sell not in trader_inst.get_open_orders()

        await trader_inst.cancel_all_open_orders_with_currency("BTC")

        assert market_buy not in trader_inst.get_open_orders()
        assert market_sell not in trader_inst.get_open_orders()
        assert limit_buy not in trader_inst.get_open_orders()
        assert limit_sell not in trader_inst.get_open_orders()

        self.stop(trader_inst)

    async def test_notify_order_close(self):
        config, _, trader_inst = await self.init_default()

        # Test buy order
        market_buy = BuyMarketOrder(trader_inst)
        market_buy.new(TraderOrderType.BUY_MARKET,
                       "BTC/EUR",
                       70,
                       10,
                       70)

        # Test buy order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(TraderOrderType.SELL_LIMIT,
                       "NANO/USDT",
                       70,
                       10,
                       70)

        # Test stop loss order
        stop_loss = StopLossOrder(trader_inst)
        stop_loss.new(TraderOrderType.STOP_LOSS,
                      "BTC/USD",
                      60,
                      10,
                      60)

        # create order notifier to prevent None call
        market_buy.order_notifier = OrderNotifier(config, market_buy)
        limit_sell.order_notifier = OrderNotifier(config, limit_sell)
        stop_loss.order_notifier = OrderNotifier(config, stop_loss)

        trader_inst.get_order_manager().add_order_to_list(market_buy)
        trader_inst.get_order_manager().add_order_to_list(stop_loss)
        trader_inst.get_order_manager().add_order_to_list(limit_sell)

        await trader_inst.notify_order_close(limit_sell, True)
        await trader_inst.notify_order_close(market_buy, True)

        assert market_buy not in trader_inst.get_open_orders()
        assert limit_sell not in trader_inst.get_open_orders()
        assert stop_loss in trader_inst.get_open_orders()

        self.stop(trader_inst)

    async def test_notify_sell_limit_order_cancel(self):
        _, _, trader_inst = await self.init_default()
        initial_portfolio = copy.deepcopy(trader_inst.portfolio.portfolio)

        # Test buy order
        limit_buy = trader_inst.create_order_instance(order_type=TraderOrderType.BUY_LIMIT,
                                                      symbol="BQX/BTC",
                                                      current_price=4,
                                                      quantity=2,
                                                      price=4)

        await trader_inst.create_order(limit_buy, trader_inst.portfolio)

        await trader_inst.notify_order_close(limit_buy, True)

        assert limit_buy not in trader_inst.get_open_orders()

        assert initial_portfolio == trader_inst.portfolio.portfolio

        self.stop(trader_inst)

    async def test_notify_sell_limit_order_cancel_one_in_two(self):
        _, _, trader_inst = await self.init_default()
        initial_portfolio = copy.deepcopy(trader_inst.portfolio.portfolio)

        # Test buy order
        limit_buy = trader_inst.create_order_instance(order_type=TraderOrderType.BUY_LIMIT,
                                                      symbol="BQX/BTC",
                                                      current_price=4,
                                                      quantity=2,
                                                      price=4)

        await trader_inst.create_order(limit_buy, trader_inst.portfolio)

        # Test second buy order
        second_limit_buy = trader_inst.create_order_instance(order_type=TraderOrderType.BUY_LIMIT,
                                                             symbol="VEN/BTC",
                                                             current_price=1,
                                                             quantity=1.5,
                                                             price=1)

        await trader_inst.create_order(second_limit_buy, trader_inst.portfolio)

        # Cancel only 1st one
        await trader_inst.notify_order_close(limit_buy, True)

        assert limit_buy not in trader_inst.get_open_orders()
        assert second_limit_buy in trader_inst.get_open_orders()

        assert initial_portfolio != trader_inst.portfolio.portfolio
        assert trader_inst.portfolio.portfolio["BTC"][Portfolio.AVAILABLE] == 8.5
        assert trader_inst.portfolio.portfolio["BTC"][Portfolio.TOTAL] == 10

        self.stop(trader_inst)

    async def test_notify_sell_limit_order_fill(self):
        _, _, trader_inst = await self.init_default()
        initial_portfolio = copy.deepcopy(trader_inst.portfolio.portfolio)

        # Test buy order
        limit_buy = trader_inst.create_order_instance(order_type=TraderOrderType.BUY_LIMIT,
                                                      symbol="BQX/BTC",
                                                      current_price=0.1,
                                                      quantity=10,
                                                      price=0.1)

        await trader_inst.create_order(limit_buy, trader_inst.portfolio)

        limit_buy.filled_price = limit_buy.origin_price
        limit_buy.filled_quantity = limit_buy.origin_quantity

        await trader_inst.notify_order_close(limit_buy)

        assert limit_buy not in trader_inst.get_open_orders()

        assert initial_portfolio != trader_inst.portfolio.portfolio
        assert trader_inst.portfolio.portfolio["BTC"][Portfolio.AVAILABLE] == 9
        assert trader_inst.portfolio.portfolio["BTC"][Portfolio.TOTAL] == 9
        assert trader_inst.portfolio.portfolio["BQX"][Portfolio.AVAILABLE] == 10
        assert trader_inst.portfolio.portfolio["BQX"][Portfolio.TOTAL] == 10

        self.stop(trader_inst)

    async def test_notify_order_close_with_linked_orders(self):
        config, _, trader_inst = await self.init_default()

        # Test buy order
        market_buy = BuyMarketOrder(trader_inst)
        market_buy.new(TraderOrderType.BUY_MARKET,
                       "BTC/EUR",
                       70,
                       10,
                       70)

        # Test buy order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(TraderOrderType.SELL_LIMIT,
                       "NANO/USDT",
                       70,
                       10,
                       70)

        # Test stop loss order
        stop_loss = StopLossOrder(trader_inst)
        stop_loss.new(TraderOrderType.STOP_LOSS,
                      "BTC/USD",
                      60,
                      10,
                      60)

        stop_loss.add_linked_order(limit_sell)
        limit_sell.add_linked_order(stop_loss)

        # create order notifier to prevent None call
        market_buy.order_notifier = OrderNotifier(config, market_buy)
        stop_loss.order_notifier = OrderNotifier(config, stop_loss)
        limit_sell.order_notifier = OrderNotifier(config, limit_sell)

        trader_inst.get_order_manager().add_order_to_list(market_buy)
        trader_inst.get_order_manager().add_order_to_list(stop_loss)
        trader_inst.get_order_manager().add_order_to_list(limit_sell)

        await trader_inst.notify_order_close(limit_sell)

        assert market_buy in trader_inst.get_open_orders()
        assert stop_loss not in trader_inst.get_open_orders()
        assert limit_sell not in trader_inst.get_open_orders()

        self.stop(trader_inst)

    async def test_parse_order_type(self):
        _, _, trader_inst = await self.init_default()

        ccxt_order_buy_market = {
            "side": TradeOrderSide.BUY,
            "type": TradeOrderType.MARKET
        }
        assert trader_inst.parse_order_type(ccxt_order_buy_market) == TraderOrderType.BUY_MARKET

        ccxt_order_buy_limit = {
            "side": TradeOrderSide.BUY,
            "type": TradeOrderType.LIMIT
        }
        assert trader_inst.parse_order_type(ccxt_order_buy_limit) == TraderOrderType.BUY_LIMIT

        ccxt_order_sell_market = {
            "side": TradeOrderSide.SELL,
            "type": TradeOrderType.MARKET
        }
        assert trader_inst.parse_order_type(ccxt_order_sell_market) == TraderOrderType.SELL_MARKET

        ccxt_order_sell_limit = {
            "side": TradeOrderSide.SELL,
            "type": TradeOrderType.LIMIT
        }
        assert trader_inst.parse_order_type(ccxt_order_sell_limit) == TraderOrderType.SELL_LIMIT

        self.stop(trader_inst)

    async def test_sell_all_currencies(self):
        _, _, trader_inst = await self.init_default()
        portfolio = trader_inst.portfolio.portfolio
        portfolio["ADA"] = {
            Portfolio.AVAILABLE: 1500,
            Portfolio.TOTAL: 1500
        }
        portfolio["USDT"] = {
            Portfolio.AVAILABLE: 1000,
            Portfolio.TOTAL: 1000
        }
        orders = await trader_inst.sell_all_currencies()
        # 1 order to sell ada, 1 order to buy btc (sell usdt), NO order for usd (not in config pairs)
        assert len(orders) == 2

        sell_ADA_order = orders[0]
        assert sell_ADA_order.symbol == "ADA/BTC"
        assert sell_ADA_order.order_type == TraderOrderType.SELL_MARKET
        assert sell_ADA_order.origin_quantity == 1500

        sell_USDT_order = orders[1]
        assert sell_USDT_order.symbol == "BTC/USDT"
        assert sell_USDT_order.order_type == TraderOrderType.BUY_MARKET
        assert round(sell_USDT_order.origin_quantity, 8) == round(1000/sell_USDT_order.origin_price, 8)

    async def test_sell_all(self):
        _, _, trader_inst = await self.init_default()
        portfolio = trader_inst.portfolio.portfolio
        portfolio["ADA"] = {
            Portfolio.AVAILABLE: 1500,
            Portfolio.TOTAL: 1500
        }
        portfolio["USDT"] = {
            Portfolio.AVAILABLE: 1000,
            Portfolio.TOTAL: 1000
        }
        orders = await trader_inst.sell_all("USDT")
        assert len(orders) == 1

        sell_USDT_order = orders[0]
        assert sell_USDT_order.symbol == "BTC/USDT"
        assert sell_USDT_order.order_type == TraderOrderType.BUY_MARKET
        assert round(sell_USDT_order.origin_quantity, 8) == round(1000/sell_USDT_order.origin_price, 8)

        orders = await trader_inst.sell_all("ADA")
        assert len(orders) == 1

        sell_ADA_order = orders[0]
        assert sell_ADA_order.symbol == "ADA/BTC"
        assert sell_ADA_order.order_type == TraderOrderType.SELL_MARKET
        assert sell_ADA_order.origin_quantity == 1500
        assert round(sell_USDT_order.origin_quantity, 8) == round(1000/sell_USDT_order.origin_price, 8)

        # currency not in portfolio
        orders = await trader_inst.sell_all("XBT")
        assert len(orders) == 0

        portfolio["XRB"] = {
            Portfolio.AVAILABLE: 0,
            Portfolio.TOTAL: 0
        }
        # currency in portfolio but with 0 quantity
        orders = await trader_inst.sell_all("XRB")
        assert len(orders) == 0

        # invalid currency
        orders = await trader_inst.sell_all("")
        assert len(orders) == 0

        portfolio["ICX"] = {
            Portfolio.AVAILABLE: 0.0000001,
            Portfolio.TOTAL: 0.0000001
        }
        # currency in portfolio but with close to 0 quantity
        orders = await trader_inst.sell_all("ICX")
        assert len(orders) == 0

    async def test_parse_exchange_order_to_trade_instance(self):
        _, exchange_inst, trader_inst = await self.init_default()

        order_to_test = Order(trader_inst)
        timestamp = time.time()

        exchange_order = {
            "status": OrderStatus.PARTIALLY_FILLED,
            "fee": 0.001,
            "price": 10.1444215411,
            "cost": 100.1444215411,
            "filled": 1.568415145687741563132,
            "timestamp": timestamp
        }

        trader_inst.parse_exchange_order_to_trade_instance(exchange_order, order_to_test)

        assert order_to_test.status == OrderStatus.PARTIALLY_FILLED
        assert order_to_test.filled_quantity == 1.568415145687741563132
        assert order_to_test.filled_price == 10.1444215411
        assert order_to_test.fee == 0.001
        assert order_to_test.total_cost == 100.1444215411
        assert order_to_test.executed_time == exchange_inst.get_uniform_timestamp(timestamp)

        self.stop(trader_inst)

    async def test_parse_exchange_order_to_order_instance(self):
        _, exchange_inst, trader_inst = await self.init_default()

        timestamp = time.time()

        exchange_order = {
            "side": TradeOrderSide.SELL,
            "type": TradeOrderType.LIMIT,
            "symbol": self.DEFAULT_SYMBOL,
            "amount": 1564.721672163722,
            "filled": 15.15467,
            "id": 1546541123,
            "status": OrderStatus.OPEN,
            "price": 10254.4515,
            "timestamp": timestamp
        }

        order_to_test = trader_inst.parse_exchange_order_to_order_instance(exchange_order)

        assert order_to_test.order_type == TraderOrderType.SELL_LIMIT
        assert order_to_test.status == OrderStatus.OPEN
        assert order_to_test.linked_to is None
        assert order_to_test.origin_stop_price is None
        assert order_to_test.origin_quantity == 1564.721672163722
        assert order_to_test.origin_price == 10254.4515
        assert order_to_test.filled_quantity == 1564.721672163722
        assert order_to_test.creation_time == exchange_inst.get_uniform_timestamp(timestamp)

        self.stop(trader_inst)
