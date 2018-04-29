import ccxt

from backtesting.exchange_simulator import ExchangeSimulator
from config.cst import TraderOrderType
from tests.test_utils.config import load_test_config
from trading.trader.order import BuyMarketOrder, OrderConstants, SellLimitOrder
from trading.trader.portfolio import Portfolio
from trading.trader.trader_simulator import TraderSimulator


class TestPortfolio:
    @staticmethod
    def init_default():
        config = load_test_config()
        portfolio_inst = Portfolio(config)
        return config, portfolio_inst

    @staticmethod
    def create_trader_and_exchanges(config):
        exchange_inst = ExchangeSimulator(config, ccxt.binance)
        trader_inst = TraderSimulator(config, exchange_inst)
        return exchange_inst, trader_inst

    def test_load_portfolio(self):
        _, portfolio_inst = self.init_default()
        portfolio_inst._load_portfolio()
        assert portfolio_inst.portfolio == {'BTC': {'available': 10, 'total': 10},
                                            'USD': {'available': 1000, 'total': 1000}
                                            }

    def test_get_currency_portfolio(self):
        _, portfolio_inst = self.init_default()
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("NANO", Portfolio.TOTAL) == 0

    def test_update_portfolio_data(self):
        _, portfolio_inst = self.init_default()
        portfolio_inst._update_portfolio_data("BTC", -5)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 5
        portfolio_inst._update_portfolio_data("BTC", -6, total=False, available=True)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 4
        portfolio_inst._update_portfolio_data("XRP", 4.5, total=True, available=True)
        assert portfolio_inst.get_currency_portfolio("XRP", Portfolio.AVAILABLE) == 4.5

    def test_update_portfolio_available(self):
        config, portfolio_inst = self.init_default()
        _, trader_inst = self.create_trader_and_exchanges(config)

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

        # test buy order filled --> return to init state and the update_portfolio will sync TOTAL with AVAILABLE
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

        # test sell order filled --> return to init state and the update_portfolio will sync TOTAL with AVAILABLE
        portfolio_inst.update_portfolio_available(limit_sell, False)
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.AVAILABLE) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.AVAILABLE) == 1000
        assert portfolio_inst.get_currency_portfolio("BTC", Portfolio.TOTAL) == 10
        assert portfolio_inst.get_currency_portfolio("USD", Portfolio.TOTAL) == 1000
