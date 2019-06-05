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
import pytest

from config import TraderOrderType, CONFIG_SIMULATOR, CONFIG_SIMULATOR_FEES, CONFIG_SIMULATOR_FEES_MAKER, \
    CONFIG_SIMULATOR_FEES_TAKER
from tests.test_utils.config import load_test_config
from tests.test_utils.order_util import fill_limit_or_stop_order, fill_market_order
from octobot_trading.exchanges import ExchangeManager
from trading.trader.order import BuyMarketOrder, SellLimitOrder, BuyLimitOrder, SellMarketOrder, \
    StopLossOrder
from trading.trader.portfolio import Portfolio
from trading.trader.trader_simulator import TraderSimulator


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestPortfolio:
    @staticmethod
    async def init_default():
        config = load_test_config()
        exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
        await exchange_manager.initialize()
        exchange_inst = exchange_manager.get_exchange()
        trader_inst = TraderSimulator(config, exchange_inst, 1)
        portfolio_inst = Portfolio(config, trader_inst)
        await portfolio_inst.initialize()
        trader_inst.stop_order_manager()
        return config, portfolio_inst, exchange_inst, trader_inst

    async def test_load_portfolio(self):
        _, portfolio_inst, _, _ = await self.init_default()
        await portfolio_inst._load_portfolio()
        assert portfolio_inst.portfolio == {
            'BTC': {'available': 10, 'total': 10},
            'USD': {'available': 1000, 'total': 1000}
        }

    async def test_get_portfolio_from_amount_dict(self):
        assert Portfolio.get_portfolio_from_amount_dict({"zyx": 10, "BTC": 1}) == {
            'zyx': {'available': 10, 'total': 10},
            'BTC': {'available': 1, 'total': 1}
        }
        assert Portfolio.get_portfolio_from_amount_dict({}) == {}
        with pytest.raises(RuntimeError):
            Portfolio.get_portfolio_from_amount_dict({"zyx": "10", "BTC": 1})

    async def test_get_currency_portfolio(self):
        _, portfolio_inst, _, _ = await self.init_default()
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("NANO", Portfolio.TOTAL) == 0

    async def test_update_portfolio_data(self):
        _, portfolio_inst, _, _ = await self.init_default()
        portfolio_inst._update_portfolio_data("BTC", -5)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 5
        portfolio_inst._update_portfolio_data("BTC", -6, total=False, available=True)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 4
        portfolio_inst._update_portfolio_data("XRP", 4.5, total=True, available=True)
        assert portfolio_inst.get_currency_portfolio("XRP", Portfolio.AVAILABLE) == 4.5

    async def test_update_portfolio_available(self):
        _, portfolio_inst, _, trader_inst = await self.init_default()

        # Test buy order
        market_buy = BuyMarketOrder(trader_inst)
        market_buy.new(TraderOrderType.BUY_MARKET,
                       "BTC/USD",
                       70,
                       10,
                       70)
        # test buy order creation
        portfolio_inst.update_portfolio_available(market_buy, True)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 300
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000

        # test buy order canceled --> return to init state and the update_portfolio will sync TOTAL with AVAILABLE
        portfolio_inst.update_portfolio_available(market_buy, False)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000

        # Test sell order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(TraderOrderType.SELL_LIMIT,
                       "BTC/USD",
                       60,
                       8,
                       60)
        # test sell order creation
        portfolio_inst.update_portfolio_available(limit_sell, True)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 2
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000

        # test sell order canceled --> return to init state and the update_portfolio will sync TOTAL with AVAILABLE
        portfolio_inst.update_portfolio_available(limit_sell, False)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000

    async def test_update_portfolio(self):
        _, portfolio_inst, _, trader_inst = await self.init_default()

        # Test buy order
        limit_buy = BuyLimitOrder(trader_inst)
        limit_buy.new(TraderOrderType.BUY_LIMIT,
                      "BTC/USD",
                      70,
                      10,
                      70)

        # update portfolio with creations
        portfolio_inst.update_portfolio_available(limit_buy, True)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 300

        await fill_limit_or_stop_order(limit_buy, 69, 71)

        await portfolio_inst.update_portfolio(limit_buy)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 20
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 300
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 20
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 300

        # Test buy order
        market_sell = SellMarketOrder(trader_inst)
        market_sell.new(TraderOrderType.SELL_MARKET,
                        "BTC/USD",
                        80,
                        8,
                        80)

        # update portfolio with creations
        portfolio_inst.update_portfolio_available(market_sell, True)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 12
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 300

        await fill_market_order(market_sell, 80)

        # when filling market sell
        await portfolio_inst.update_portfolio(market_sell)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 12
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 940
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 12
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 940

    async def test_update_portfolio_with_filled_orders(self):
        _, portfolio_inst, exchange_inst, trader_inst = await self.init_default()

        # force fees => should have consequences
        exchange_inst.config[CONFIG_SIMULATOR][CONFIG_SIMULATOR_FEES] = {
            CONFIG_SIMULATOR_FEES_MAKER: 0.05,
            CONFIG_SIMULATOR_FEES_TAKER: 0.1
        }

        # Test buy order
        market_sell = SellMarketOrder(trader_inst)
        market_sell.new(TraderOrderType.SELL_MARKET,
                        "BTC/USD",
                        70,
                        3,
                        70)

        await fill_market_order(market_sell, 70)

        # Test sell order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(TraderOrderType.SELL_LIMIT,
                       "BTC/USD",
                       100,
                       4.2,
                       100)

        # Test stop loss order
        stop_loss = StopLossOrder(trader_inst)
        stop_loss.new(TraderOrderType.STOP_LOSS,
                      "BTC/USD",
                      80,
                      4.2,
                      80)

        limit_sell.add_linked_order(stop_loss)
        stop_loss.add_linked_order(limit_sell)

        # Test buy order
        limit_buy = BuyLimitOrder(trader_inst)
        limit_buy.new(TraderOrderType.BUY_LIMIT,
                      "BTC/USD",
                      50,
                      2,
                      50)

        await fill_limit_or_stop_order(limit_buy, 49, 51)

        # update portfolio with creations
        portfolio_inst.update_portfolio_available(market_sell, True)
        portfolio_inst.update_portfolio_available(limit_sell, True)
        portfolio_inst.update_portfolio_available(stop_loss, True)
        portfolio_inst.update_portfolio_available(limit_buy, True)

        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 2.8
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 900

        # when cancelling limit sell, market sell and stop orders
        portfolio_inst.update_portfolio_available(stop_loss, False)
        portfolio_inst.update_portfolio_available(limit_sell, False)

        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 7
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 900

        # when filling limit buy
        await portfolio_inst.update_portfolio(limit_buy)

        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 8.999
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 900
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 11.999
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 900

        # when filling market sell
        await portfolio_inst.update_portfolio(market_sell)

        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 8.999
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1109.79
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 8.999
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1109.79

    async def test_update_portfolio_with_cancelled_orders(self):
        _, portfolio_inst, exchange_inst, trader_inst = await self.init_default()

        # force fees => shouldn't do anything
        exchange_inst.config[CONFIG_SIMULATOR][CONFIG_SIMULATOR_FEES] = {
            CONFIG_SIMULATOR_FEES_MAKER: 0.05,
            CONFIG_SIMULATOR_FEES_TAKER: 0.1
        }

        # Test buy order
        market_sell = SellMarketOrder(trader_inst)
        market_sell.new(TraderOrderType.SELL_MARKET,
                        "BTC/USD",
                        80,
                        4.1,
                        80)

        # Test sell order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(TraderOrderType.SELL_LIMIT,
                       "BTC/USD",
                       10,
                       4.2,
                       10)

        # Test stop loss order
        stop_loss = StopLossOrder(trader_inst)
        stop_loss.new(TraderOrderType.STOP_LOSS,
                      "BTC/USD",
                      80,
                      3.6,
                      80)

        portfolio_inst.update_portfolio_available(stop_loss, True)
        portfolio_inst.update_portfolio_available(limit_sell, True)

        # Test buy order
        limit_buy = BuyLimitOrder(trader_inst)
        limit_buy.new(TraderOrderType.BUY_LIMIT,
                      "BTC/USD",
                      50,
                      4,
                      50)

        portfolio_inst.update_portfolio_available(limit_buy, True)
        portfolio_inst.update_portfolio_available(market_sell, True)

        assert round(portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE), 1) == 1.7
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 800
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000

        # with no filled orders
        portfolio_inst.update_portfolio_available(stop_loss, False)
        portfolio_inst.update_portfolio_available(limit_sell, False)
        portfolio_inst.update_portfolio_available(limit_buy, False)
        portfolio_inst.update_portfolio_available(market_sell, False)

        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000

    async def test_update_portfolio_with_stop_loss_orders(self):
        _, portfolio_inst, _, trader_inst = await self.init_default()

        # Test buy order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(TraderOrderType.SELL_LIMIT,
                       "BTC/USD",
                       90,
                       4,
                       90)

        # Test buy order
        limit_buy = BuyLimitOrder(trader_inst)
        limit_buy.new(TraderOrderType.BUY_LIMIT,
                      "BTC/USD",
                      50,
                      4,
                      50)

        # Test stop loss order
        stop_loss = StopLossOrder(trader_inst)
        stop_loss.new(TraderOrderType.STOP_LOSS,
                      "BTC/USD",
                      60,
                      4,
                      60)

        await fill_limit_or_stop_order(stop_loss, 59, 61)

        portfolio_inst.update_portfolio_available(stop_loss, True)
        portfolio_inst.update_portfolio_available(limit_sell, True)
        portfolio_inst.update_portfolio_available(limit_buy, True)

        assert round(portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE), 1) == 6
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 800
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000

        # cancel limits
        portfolio_inst.update_portfolio_available(limit_buy, False)
        portfolio_inst.update_portfolio_available(limit_sell, False)

        # filling stop loss
        # typical stop loss behavior --> update available before update portfolio
        await portfolio_inst.update_portfolio(stop_loss)

        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 6
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1240
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 6
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1240

    async def test_update_portfolio_with_some_filled_orders(self):
        _, portfolio_inst, _, trader_inst = await self.init_default()

        # Test buy order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(TraderOrderType.SELL_LIMIT,
                       "BTC/USD",
                       90,
                       4,
                       90)

        # Test buy order
        limit_buy = BuyLimitOrder(trader_inst)
        limit_buy.new(TraderOrderType.BUY_LIMIT,
                      "BTC/USD",
                      60,
                      2,
                      60)

        # Test buy order
        limit_buy_2 = BuyLimitOrder(trader_inst)
        limit_buy_2.new(TraderOrderType.BUY_LIMIT,
                        "BTC/USD",
                        50,
                        4,
                        50)

        # Test sell order
        limit_sell_2 = SellLimitOrder(trader_inst)
        limit_sell_2.new(TraderOrderType.SELL_LIMIT,
                         "BTC/USD",
                         10,
                         2,
                         10)

        # Test stop loss order
        stop_loss_2 = StopLossOrder(trader_inst)
        stop_loss_2.new(TraderOrderType.STOP_LOSS,
                        "BTC/USD",
                        10,
                        2,
                        10)

        # Test sell order
        limit_sell_3 = SellLimitOrder(trader_inst)
        limit_sell_3.new(TraderOrderType.SELL_LIMIT,
                         "BTC/USD",
                         20,
                         1,
                         20)

        # Test stop loss order
        stop_loss_3 = StopLossOrder(trader_inst)
        stop_loss_3.new(TraderOrderType.STOP_LOSS,
                        "BTC/USD",
                        20,
                        1,
                        20)

        portfolio_inst.update_portfolio_available(stop_loss_2, True)
        portfolio_inst.update_portfolio_available(stop_loss_3, True)
        portfolio_inst.update_portfolio_available(limit_sell, True)
        portfolio_inst.update_portfolio_available(limit_sell_2, True)
        portfolio_inst.update_portfolio_available(limit_sell_3, True)
        portfolio_inst.update_portfolio_available(limit_buy, True)
        portfolio_inst.update_portfolio_available(limit_buy_2, True)

        assert round(portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE), 1) == 3
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 680
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000

        # cancels
        portfolio_inst.update_portfolio_available(stop_loss_3, False)
        portfolio_inst.update_portfolio_available(limit_sell_2, False)
        portfolio_inst.update_portfolio_available(limit_buy, False)

        # filling
        await fill_limit_or_stop_order(stop_loss_2, 9, 11)
        await fill_limit_or_stop_order(limit_sell, 89, 91)
        await fill_limit_or_stop_order(limit_sell_3, 19, 21)
        await fill_limit_or_stop_order(limit_buy_2, 49, 51)

        await portfolio_inst.update_portfolio(stop_loss_2)
        await portfolio_inst.update_portfolio(limit_sell)
        await portfolio_inst.update_portfolio(limit_sell_3)
        await portfolio_inst.update_portfolio(limit_buy_2)

        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 7
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1200
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 7
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1200

    async def test_update_portfolio_with_multiple_filled_orders(self):
        _, portfolio_inst, _, trader_inst = await self.init_default()

        # Test buy order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(TraderOrderType.SELL_LIMIT,
                       "BTC/USD",
                       90,
                       4,
                       90)

        # Test buy order
        limit_buy = BuyLimitOrder(trader_inst)
        limit_buy.new(TraderOrderType.BUY_LIMIT,
                      "BTC/USD",
                      60,
                      2,
                      60)

        # Test buy order
        limit_buy_2 = BuyLimitOrder(trader_inst)
        limit_buy_2.new(TraderOrderType.BUY_LIMIT,
                        "BTC/USD",
                        50,
                        4,
                        50)

        # Test buy order
        limit_buy_3 = BuyLimitOrder(trader_inst)
        limit_buy_3.new(TraderOrderType.BUY_LIMIT,
                        "BTC/USD",
                        46,
                        2,
                        46)

        # Test buy order
        limit_buy_4 = BuyLimitOrder(trader_inst)
        limit_buy_4.new(TraderOrderType.BUY_LIMIT,
                        "BTC/USD",
                        41,
                        1.78,
                        41)

        # Test buy order
        limit_buy_5 = BuyLimitOrder(trader_inst)
        limit_buy_5.new(TraderOrderType.BUY_LIMIT,
                        "BTC/USD",
                        0.2122427,
                        3.72448,
                        0.2122427)

        # Test buy order
        limit_buy_6 = BuyLimitOrder(trader_inst)
        limit_buy_6.new(TraderOrderType.BUY_LIMIT,
                        "BTC/USD",
                        430,
                        1.05,
                        430)

        # Test sell order
        limit_sell_2 = SellLimitOrder(trader_inst)
        limit_sell_2.new(TraderOrderType.SELL_LIMIT,
                         "BTC/USD",
                         10,
                         2,
                         10)

        # Test stop loss order
        stop_loss_2 = StopLossOrder(trader_inst)
        stop_loss_2.new(TraderOrderType.STOP_LOSS,
                        "BTC/USD",
                        10,
                        2,
                        10)

        # Test sell order
        limit_sell_3 = SellLimitOrder(trader_inst)
        limit_sell_3.new(TraderOrderType.SELL_LIMIT,
                         "BTC/USD",
                         20,
                         1,
                         20)

        # Test stop loss order
        stop_loss_3 = StopLossOrder(trader_inst)
        stop_loss_3.new(TraderOrderType.STOP_LOSS,
                        "BTC/USD",
                        20,
                        1,
                        20)

        # Test sell order
        limit_sell_4 = SellLimitOrder(trader_inst)
        limit_sell_4.new(TraderOrderType.SELL_LIMIT,
                         "BTC/USD",
                         50,
                         0.2,
                         50)

        # Test stop loss order
        stop_loss_4 = StopLossOrder(trader_inst)
        stop_loss_4.new(TraderOrderType.STOP_LOSS,
                        "BTC/USD",
                        45,
                        0.2,
                        45)

        # Test sell order
        limit_sell_5 = SellLimitOrder(trader_inst)
        limit_sell_5.new(TraderOrderType.SELL_LIMIT,
                         "BTC/USD",
                         11,
                         0.7,
                         11)

        # Test stop loss order
        stop_loss_5 = StopLossOrder(trader_inst)
        stop_loss_5.new(TraderOrderType.STOP_LOSS,
                        "BTC/USD",
                        9,
                        0.7,
                        9)

        portfolio_inst.update_portfolio_available(stop_loss_2, True)
        portfolio_inst.update_portfolio_available(stop_loss_3, True)
        portfolio_inst.update_portfolio_available(stop_loss_4, True)
        portfolio_inst.update_portfolio_available(stop_loss_5, True)
        portfolio_inst.update_portfolio_available(limit_sell, True)
        portfolio_inst.update_portfolio_available(limit_sell_2, True)
        portfolio_inst.update_portfolio_available(limit_sell_3, True)
        portfolio_inst.update_portfolio_available(limit_sell_4, True)
        portfolio_inst.update_portfolio_available(limit_sell_5, True)
        portfolio_inst.update_portfolio_available(limit_buy, True)
        portfolio_inst.update_portfolio_available(limit_buy_2, True)
        portfolio_inst.update_portfolio_available(limit_buy_3, True)
        portfolio_inst.update_portfolio_available(limit_buy_4, True)
        portfolio_inst.update_portfolio_available(limit_buy_5, True)
        portfolio_inst.update_portfolio_available(limit_buy_6, True)

        assert round(portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE), 1) == 2.1
        assert round(portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE), 7) == 62.7295063
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000

        # cancels
        portfolio_inst.update_portfolio_available(stop_loss_3, False)
        portfolio_inst.update_portfolio_available(stop_loss_5, False)
        portfolio_inst.update_portfolio_available(limit_sell_2, False)
        portfolio_inst.update_portfolio_available(limit_buy, False)
        portfolio_inst.update_portfolio_available(limit_buy_3, False)
        portfolio_inst.update_portfolio_available(limit_buy_5, False)
        portfolio_inst.update_portfolio_available(limit_sell_4, False)

        # filling
        await fill_limit_or_stop_order(stop_loss_2, 9, 11)
        await fill_limit_or_stop_order(limit_sell, 89, 91)
        await fill_limit_or_stop_order(limit_sell_3, 19, 21)
        await fill_limit_or_stop_order(limit_buy_2, 49, 51)
        await fill_limit_or_stop_order(limit_sell_5, 9, 12)
        await fill_limit_or_stop_order(stop_loss_4, 44, 46)
        await fill_limit_or_stop_order(limit_buy_4, 40, 42)
        await fill_limit_or_stop_order(limit_buy_5, 0.2122426, 0.2122428)
        await fill_limit_or_stop_order(limit_buy_6, 429, 431)

        await portfolio_inst.update_portfolio(stop_loss_2)
        await portfolio_inst.update_portfolio(limit_buy_4)
        await portfolio_inst.update_portfolio(limit_sell)
        await portfolio_inst.update_portfolio(limit_sell_3)
        await portfolio_inst.update_portfolio(limit_buy_2)
        await portfolio_inst.update_portfolio(limit_sell_5)
        await portfolio_inst.update_portfolio(stop_loss_4)
        await portfolio_inst.update_portfolio(limit_buy_5)
        await portfolio_inst.update_portfolio(limit_buy_6)

        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 12.65448
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 692.22
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 12.65448
        assert round(portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL), 7) == 691.4295063

    async def test_update_portfolio_with_multiple_symbols_orders(self):
        _, portfolio_inst, _, trader_inst = await self.init_default()

        # Test buy order
        market_buy = BuyMarketOrder(trader_inst)
        market_buy.new(TraderOrderType.BUY_MARKET,
                       "ETH/USD",
                       7,
                       100,
                       7)

        # test buy order creation
        portfolio_inst.update_portfolio_available(market_buy, True)
        assert portfolio_inst.get_currency_portfolio("ETH", Portfolio.AVAILABLE) == 0
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 300
        assert portfolio_inst.get_currency_portfolio("ETH", Portfolio.TOTAL) == 0
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000

        await fill_market_order(market_buy, 7)

        await portfolio_inst.update_portfolio(market_buy)
        assert portfolio_inst.get_currency_portfolio("ETH", Portfolio.AVAILABLE) == 100
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 300
        assert portfolio_inst.get_currency_portfolio("ETH", Portfolio.TOTAL) == 100
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 300

        # Test buy order
        market_buy = BuyMarketOrder(trader_inst)
        market_buy.new(TraderOrderType.BUY_MARKET,
                       "LTC/BTC",
                       0.0135222,
                       100,
                       0.0135222)

        # test buy order creation
        portfolio_inst.update_portfolio_available(market_buy, True)
        assert portfolio_inst.get_currency_portfolio("LTC", Portfolio.AVAILABLE) == 0
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 8.647780000000001
        assert portfolio_inst.get_currency_portfolio("LTC", Portfolio.TOTAL) == 0
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10

        await fill_market_order(market_buy, 0.0135222)

        await portfolio_inst.update_portfolio(market_buy)
        assert portfolio_inst.get_currency_portfolio("LTC", Portfolio.AVAILABLE) == 100
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 8.647780000000001
        assert portfolio_inst.get_currency_portfolio("LTC", Portfolio.TOTAL) == 100
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 8.647780000000001

        # Test buy order
        limit_buy = BuyLimitOrder(trader_inst)
        limit_buy.new(TraderOrderType.BUY_LIMIT,
                      "XRP/BTC",
                      0.00012232132312312,
                      3000.1214545,
                      0.00012232132312312)

        # test buy order creation
        portfolio_inst.update_portfolio_available(limit_buy, True)
        assert portfolio_inst.get_currency_portfolio("XRP", Portfolio.AVAILABLE) == 0
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 8.280801174155501
        assert portfolio_inst.get_currency_portfolio("XRP", Portfolio.TOTAL) == 0
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 8.647780000000001

        # cancel
        portfolio_inst.update_portfolio_available(limit_buy, False)
        assert portfolio_inst.get_currency_portfolio("XRP", Portfolio.AVAILABLE) == 0
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 8.647780000000001
        assert portfolio_inst.get_currency_portfolio("XRP", Portfolio.TOTAL) == 0
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 8.647780000000001

    async def test_reset_portfolio_available(self):
        _, portfolio_inst, _, trader_inst = await self.init_default()

        # Test buy order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(TraderOrderType.SELL_LIMIT,
                       "BTC/USD",
                       90,
                       4,
                       90)

        portfolio_inst.update_portfolio_available(limit_sell, True)
        portfolio_inst.reset_portfolio_available()

        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000

        # Test sell order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(TraderOrderType.SELL_LIMIT,
                       "BTC/USD",
                       90,
                       4,
                       90)

        portfolio_inst.update_portfolio_available(limit_sell, True)
        # Test buy order
        limit_buy = BuyLimitOrder(trader_inst)
        limit_buy.new(TraderOrderType.BUY_LIMIT,
                      "VEN/BTC",
                      0.5,
                      4,
                      0.5)

        portfolio_inst.update_portfolio_available(limit_buy, True)

        # Test buy order
        btc_limit_buy = BuyLimitOrder(trader_inst)
        btc_limit_buy.new(TraderOrderType.BUY_LIMIT,
                          "BTC/USD",
                          10,
                          50,
                          10)

        portfolio_inst.update_portfolio_available(btc_limit_buy, True)

        # Test buy order
        btc_limit_buy2 = BuyLimitOrder(trader_inst)
        btc_limit_buy2.new(TraderOrderType.BUY_LIMIT,
                           "BTC/USD",
                           10,
                           50,
                           10)

        portfolio_inst.update_portfolio_available(btc_limit_buy2, True)

        # reset equivalent of the ven buy order
        portfolio_inst.reset_portfolio_available("BTC", 4*0.5)

        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 6
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 0
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000

        # reset equivalent of the btc buy orders 1 and 2
        portfolio_inst.reset_portfolio_available("USD")

        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 6
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000
