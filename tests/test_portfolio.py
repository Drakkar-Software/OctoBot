import ccxt

from backtesting.exchange_simulator import ExchangeSimulator
from config.config import load_config
from trading.trader.portfolio import Portfolio
from trading.trader.trader_simulator import TraderSimulator


class TestPortfolio(object):
    def init_default(self):
        config = load_config("tests/static/config.json")
        exchange_inst = ExchangeSimulator(config, ccxt.binance)
        trader_inst = TraderSimulator(config, exchange_inst)
        portfolio_inst = Portfolio(config, trader_inst)
        return config, exchange_inst, trader_inst, portfolio_inst

    def _load_portfolio_without_config(self):
        config = None
        test_inst = Portfolio(config, None)
        test_inst._load_portfolio()
        assert test_inst.portfolio is {}
