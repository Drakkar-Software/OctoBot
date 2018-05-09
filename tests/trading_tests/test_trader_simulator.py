import ccxt

from backtesting.exchange_simulator import ExchangeSimulator
from tests.test_utils.config import load_test_config
from trading.trader.trader_simulator import TraderSimulator


class TestTraderSimulator:
    @staticmethod
    def init_default():
        config = load_test_config()
        exchange_inst = ExchangeSimulator(config, ccxt.binance)
        trader_sim_inst = TraderSimulator(config, exchange_inst)
        return config, exchange_inst, trader_sim_inst

    @staticmethod
    def stop(trader):
        trader.stop_order_manager()

    def test_create_order(self):
        pass
