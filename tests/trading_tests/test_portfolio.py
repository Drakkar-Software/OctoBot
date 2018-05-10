import random

import ccxt

from backtesting.exchange_simulator import ExchangeSimulator
from config.cst import TraderOrderType, SIMULATOR_LAST_PRICES_TO_CHECK
from tests.test_utils.config import load_test_config
from trading.trader.order import BuyMarketOrder, OrderConstants, SellLimitOrder, BuyLimitOrder, SellMarketOrder, \
    StopLossOrder
from trading.trader.portfolio import Portfolio
from trading.trader.trader_simulator import TraderSimulator


class TestPortfolio:
    @staticmethod
    def init_default():
        config = load_test_config()
        exchange_inst = ExchangeSimulator(config, ccxt.binance)
        trader_inst = TraderSimulator(config, exchange_inst)
        portfolio_inst = Portfolio(config, trader_inst)
        return config, portfolio_inst, exchange_inst, trader_inst

    @staticmethod
    def stop(trader):
        trader.stop_order_manager()

    def test_load_portfolio(self):
        _, portfolio_inst, _, trader_inst = self.init_default()
        portfolio_inst._load_portfolio()
        assert portfolio_inst.portfolio == {'BTC': {'available': 10, 'total': 10},
                                            'USD': {'available': 1000, 'total': 1000}
                                            }

        self.stop(trader_inst)

    def test_get_currency_portfolio(self):
        _, portfolio_inst, _, trader_inst = self.init_default()
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("NANO", Portfolio.TOTAL) == 0

        self.stop(trader_inst)

    def test_update_portfolio_data(self):
        _, portfolio_inst, _, trader_inst = self.init_default()
        portfolio_inst._update_portfolio_data("BTC", -5)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 5
        portfolio_inst._update_portfolio_data("BTC", -6, total=False, available=True)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 4
        portfolio_inst._update_portfolio_data("XRP", 4.5, total=True, available=True)
        assert portfolio_inst.get_currency_portfolio("XRP", Portfolio.AVAILABLE) == 4.5

        self.stop(trader_inst)

    def test_update_portfolio_available(self):
        config, portfolio_inst, _, trader_inst = self.init_default()

        # Test buy order
        market_buy = BuyMarketOrder(trader_inst)
        market_buy.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.BUY_MARKET],
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
        limit_sell.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.SELL_LIMIT],
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

        self.stop(trader_inst)

    def test_update_portfolio(self):
        config, portfolio_inst, _, trader_inst = self.init_default()

        # Test buy order
        limit_buy = BuyLimitOrder(trader_inst)
        limit_buy.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.BUY_LIMIT],
                      "BTC/USD",
                      70,
                      10,
                      70)

        # update portfolio with creations
        portfolio_inst.update_portfolio_available(limit_buy, True)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 300

        last_prices = []
        for i in range(0, SIMULATOR_LAST_PRICES_TO_CHECK):
            last_prices.insert(i, {})
            last_prices[i]["price"] = random.uniform(69, 71)

        limit_buy.last_prices = last_prices
        limit_buy.update_order_status()

        portfolio_inst.update_portfolio(limit_buy)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 20
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 300
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 20
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 300

        # Test buy order
        market_sell = SellMarketOrder(trader_inst)
        market_sell.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.SELL_MARKET],
                        "BTC/USD",
                        80,
                        8,
                        80)

        # update portfolio with creations
        portfolio_inst.update_portfolio_available(market_sell, True)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 12
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 300

        last_prices = [{
            "price": 80
        }]

        market_sell.last_prices = last_prices
        market_sell.update_order_status()

        # when filling market sell
        portfolio_inst.update_portfolio(market_sell)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 12
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 940
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 12
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 940

        self.stop(trader_inst)

    def test_update_portfolio_with_filled_orders(self):
        config, portfolio_inst, _, trader_inst = self.init_default()

        # Test buy order
        market_sell = SellMarketOrder(trader_inst)
        market_sell.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.SELL_MARKET],
                        "BTC/USD",
                        70,
                        3,
                        70)
        last_prices = [{
            "price": 70
        }]

        market_sell.last_prices = last_prices
        market_sell.update_order_status()

        # Test sell order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.SELL_LIMIT],
                       "BTC/USD",
                       100,
                       4.2,
                       100)

        # Test stop loss order
        stop_loss = StopLossOrder(trader_inst)
        stop_loss.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.STOP_LOSS],
                      "BTC/USD",
                      80,
                      4.2,
                      80)

        limit_sell.add_linked_order(stop_loss)
        stop_loss.add_linked_order(limit_sell)

        # Test buy order
        limit_buy = BuyLimitOrder(trader_inst)
        limit_buy.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.BUY_LIMIT],
                      "BTC/USD",
                      50,
                      2,
                      50)

        last_prices = []
        for i in range(0, SIMULATOR_LAST_PRICES_TO_CHECK):
            last_prices.insert(i, {})
            last_prices[i]["price"] = random.uniform(49, 51)

        limit_buy.last_prices = last_prices
        limit_buy.update_order_status()

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
        portfolio_inst.update_portfolio(limit_buy)

        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 9
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 900
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 12
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 900

        # when filling market sell
        portfolio_inst.update_portfolio(market_sell)

        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 9
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1110
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 9
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1110

        self.stop(trader_inst)

    def test_update_portfolio_with_cancelled_orders(self):
        config, portfolio_inst, _, trader_inst = self.init_default()

        # Test buy order
        market_sell = SellMarketOrder(trader_inst)
        market_sell.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.SELL_MARKET],
                        "BTC/USD",
                        80,
                        4.1,
                        80)

        # Test sell order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.SELL_LIMIT],
                       "BTC/USD",
                       10,
                       4.2,
                       10)

        # Test stop loss order
        stop_loss = StopLossOrder(trader_inst)
        stop_loss.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.STOP_LOSS],
                      "BTC/USD",
                      80,
                      3.6,
                      80)

        portfolio_inst.update_portfolio_available(stop_loss, True)
        portfolio_inst.update_portfolio_available(limit_sell, True)

        # Test buy order
        limit_buy = BuyLimitOrder(trader_inst)
        limit_buy.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.BUY_LIMIT],
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

        portfolio_inst.update_portfolio_available(stop_loss, False)
        portfolio_inst.update_portfolio_available(limit_sell, False)
        portfolio_inst.update_portfolio_available(limit_buy, False)
        portfolio_inst.update_portfolio_available(market_sell, False)

        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000

        self.stop(trader_inst)

    def test_update_portfolio_with_stop_loss_orders(self):
        config, portfolio_inst, _, trader_inst = self.init_default()

        # Test buy order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.SELL_LIMIT],
                       "BTC/USD",
                       90,
                       4,
                       90)

        # Test buy order
        limit_buy = BuyLimitOrder(trader_inst)
        limit_buy.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.BUY_LIMIT],
                      "BTC/USD",
                      50,
                      4,
                      50)

        # Test stop loss order
        stop_loss = StopLossOrder(trader_inst)
        stop_loss.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.STOP_LOSS],
                      "BTC/USD",
                      60,
                      4,
                      60)

        last_prices = []
        for i in range(0, SIMULATOR_LAST_PRICES_TO_CHECK):
            last_prices.insert(i, {})
            last_prices[i]["price"] = random.uniform(59, 61)

        stop_loss.last_prices = last_prices
        stop_loss.update_order_status()

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
        portfolio_inst.update_portfolio(stop_loss)

        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 6
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1240
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 6
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1240

        self.stop(trader_inst)

    def test_reset_portfolio_available(self):
        config, portfolio_inst, _, trader_inst = self.init_default()

        # Test buy order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.SELL_LIMIT],
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

        self.stop(trader_inst)
