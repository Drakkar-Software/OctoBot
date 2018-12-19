import ccxt

from config import TraderOrderType
from tests.test_utils.config import load_test_config
from tests.test_utils.order_util import fill_market_order, fill_limit_or_stop_order
from trading.exchanges.exchange_manager import ExchangeManager
from trading.trader.order import BuyMarketOrder, OrderConstants, SellLimitOrder, BuyLimitOrder, SellMarketOrder
from trading.trader.portfolio import Portfolio
from trading.trader.sub_portfolio import SubPortfolio
from trading.trader.trader_simulator import TraderSimulator


class TestSubPortfolio:
    DEFAULT_PERCENT = 0.4

    @staticmethod
    def init_default():
        config = load_test_config()
        exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
        exchange_inst = exchange_manager.get_exchange()
        trader_inst = TraderSimulator(config, exchange_inst, 1)
        portfolio_inst = Portfolio(config, trader_inst)
        trader_inst.stop_order_manager()
        sub_portfolio_inst = SubPortfolio(config, trader_inst, portfolio_inst, TestSubPortfolio.DEFAULT_PERCENT)
        return config, portfolio_inst, exchange_inst, trader_inst, sub_portfolio_inst

    def test_load_portfolio(self):
        _, _, _, _, sub_portfolio_inst = self.init_default()
        sub_portfolio_inst._load_portfolio()
        assert sub_portfolio_inst.portfolio == {'BTC': {'available': 10 * self.DEFAULT_PERCENT,
                                                        'total': 10 * self.DEFAULT_PERCENT},
                                                'USD': {'available': 1000 * self.DEFAULT_PERCENT,
                                                        'total': 1000 * self.DEFAULT_PERCENT}
                                                }

    def test_get_currency_portfolio(self):
        _, _, _, _, sub_portfolio_inst = self.init_default()
        assert sub_portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10 * self.DEFAULT_PERCENT
        assert sub_portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10 * self.DEFAULT_PERCENT
        assert sub_portfolio_inst.get_currency_portfolio("NANO", Portfolio.TOTAL) == 0

    def test_get_currency_multiple_sub_portfolio(self):
        config, portfolio_inst, exchange_inst, trader_inst, sub_portfolio_inst = self.init_default()

        sub_portfolio_inst_2 = SubPortfolio(config, trader_inst, portfolio_inst, 0.2)
        sub_portfolio_inst_3 = SubPortfolio(config, trader_inst, portfolio_inst, 0.1)
        sub_portfolio_inst_4 = SubPortfolio(config, trader_inst, portfolio_inst, 0.7)

        assert sub_portfolio_inst_2.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10 * 0.2
        assert sub_portfolio_inst_2.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10 * 0.2
        assert sub_portfolio_inst_2.get_currency_portfolio("NANO", Portfolio.TOTAL) == 0

        assert sub_portfolio_inst_3.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10 * 0.1
        assert sub_portfolio_inst_3.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10 * 0.1
        assert sub_portfolio_inst_3.get_currency_portfolio("NANO", Portfolio.TOTAL) == 0

        assert sub_portfolio_inst_4.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10 * 0.7
        assert sub_portfolio_inst_4.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10 * 0.7
        assert sub_portfolio_inst_4.get_currency_portfolio("NANO", Portfolio.TOTAL) == 0

    def test_update_portfolio_available(self):
        _, portfolio_inst, _, trader_inst, sub_portfolio_inst = self.init_default()

        # Test buy order
        market_buy = BuyMarketOrder(trader_inst)
        market_buy.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.BUY_MARKET],
                       "BTC/USD",
                       70,
                       10,
                       70)

        # test sub
        # test buy order creation
        sub_portfolio_inst.update_portfolio_available(market_buy, True)
        assert sub_portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10 * self.DEFAULT_PERCENT
        assert sub_portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000*self.DEFAULT_PERCENT-700
        assert sub_portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10 * self.DEFAULT_PERCENT
        assert sub_portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000 * self.DEFAULT_PERCENT
        # test parent
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 300
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000

        # test buy order canceled --> return to init state and the update_portfolio will sync TOTAL with AVAILABLE
        sub_portfolio_inst.update_portfolio_available(market_buy, False)
        assert sub_portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10 * self.DEFAULT_PERCENT
        assert sub_portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000 * self.DEFAULT_PERCENT
        assert sub_portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10 * self.DEFAULT_PERCENT
        assert sub_portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000 * self.DEFAULT_PERCENT

        # test parent
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

        # test sub
        # test sell order creation
        sub_portfolio_inst.update_portfolio_available(limit_sell, True)
        assert sub_portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10 * self.DEFAULT_PERCENT - 8
        assert sub_portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000 * self.DEFAULT_PERCENT
        assert sub_portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10 * self.DEFAULT_PERCENT
        assert sub_portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000 * self.DEFAULT_PERCENT
        # test parent
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 2
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000

        # test sell order canceled --> return to init state and the update_portfolio will sync TOTAL with AVAILABLE
        sub_portfolio_inst.update_portfolio_available(limit_sell, False)
        assert sub_portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10 * self.DEFAULT_PERCENT
        assert sub_portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000 * self.DEFAULT_PERCENT
        assert sub_portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10 * self.DEFAULT_PERCENT
        assert sub_portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000 * self.DEFAULT_PERCENT

        # test parent
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000

    def test_update_portfolio(self):
        _, portfolio_inst, _, trader_inst, sub_portfolio_inst = self.init_default()

        # Test buy order
        limit_buy = BuyLimitOrder(trader_inst)
        limit_buy.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.BUY_LIMIT],
                      "BTC/USD",
                      70,
                      10,
                      70)

        # update portfolio with creations
        sub_portfolio_inst.update_portfolio_available(limit_buy, True)
        assert sub_portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10 * self.DEFAULT_PERCENT
        assert sub_portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000*self.DEFAULT_PERCENT - 700

        # test parent
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 300

        fill_limit_or_stop_order(limit_buy, 69, 71)

        sub_portfolio_inst.update_portfolio(limit_buy)
        assert sub_portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == (10 * self.DEFAULT_PERCENT)+10
        assert sub_portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000*self.DEFAULT_PERCENT-700
        assert sub_portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == (10 * self.DEFAULT_PERCENT) + 10
        assert sub_portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000 * self.DEFAULT_PERCENT - 700

        # test parent
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
        sub_portfolio_inst.update_portfolio_available(market_sell, True)
        assert sub_portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10*self.DEFAULT_PERCENT + 2
        assert sub_portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000*self.DEFAULT_PERCENT-700

        # test parent
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 12
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 300

        fill_market_order(market_sell, 80)

        # when filling market sell
        sub_portfolio_inst.update_portfolio(market_sell)
        assert sub_portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10*self.DEFAULT_PERCENT + 2
        assert sub_portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000*self.DEFAULT_PERCENT-60
        assert sub_portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10*self.DEFAULT_PERCENT + 2
        assert sub_portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000*self.DEFAULT_PERCENT-60

        # test parent
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 12
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 940
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 12
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 940

    def test_reset_portfolio_available(self):
        _, portfolio_inst, _, trader_inst, sub_portfolio_inst = self.init_default()

        # Test buy order
        limit_sell = SellLimitOrder(trader_inst)
        limit_sell.new(OrderConstants.TraderOrderTypeClasses[TraderOrderType.SELL_LIMIT],
                       "BTC/USD",
                       90,
                       4,
                       90)

        sub_portfolio_inst.update_portfolio_available(limit_sell, True)
        sub_portfolio_inst.reset_portfolio_available()
        assert sub_portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10*self.DEFAULT_PERCENT
        assert sub_portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000*self.DEFAULT_PERCENT
        assert sub_portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10*self.DEFAULT_PERCENT
        assert sub_portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000*self.DEFAULT_PERCENT

        # test parent
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000
