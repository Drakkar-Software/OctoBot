import ccxt

from backtesting.exchange_simulator import ExchangeSimulator
from tests.test_utils.config import load_test_config
from trading.trader.portfolio import Portfolio
from trading.trader.trader_simulator import TraderSimulator


class TestPortfolio:
    @staticmethod
    def init_default():
        config = load_test_config()
        exchange_inst = ExchangeSimulator(config, ccxt.binance)
        trader_inst = TraderSimulator(config, exchange_inst)
        portfolio_inst = Portfolio(config, trader_inst)
        return config, exchange_inst, trader_inst, portfolio_inst

    def test_load_portfolio(self):
        config, exchange_inst, trader_inst, portfolio_inst = self.init_default()

        test_inst = Portfolio(config, trader_inst)
        test_inst._load_portfolio()
        assert test_inst.portfolio == {'BTC': {'available': 10, 'total': 10},
                                       'USDT': {'available': 1000, 'total': 1000}
                                       }
