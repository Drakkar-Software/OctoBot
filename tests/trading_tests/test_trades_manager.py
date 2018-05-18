import ccxt

from trading.exchanges.exchange_simulator import ExchangeSimulator
from config.cst import *
from tests.test_utils.config import load_test_config
from trading.trader.trader import Trader
from trading.trader.trades_manager import TradesManager


class TestTradesManager:
    @staticmethod
    def init_default():
        config = load_test_config()
        exchange_inst = ExchangeSimulator(config, ccxt.binance)
        trader_inst = Trader(config, exchange_inst)
        trades_manager_inst = trader_inst.get_trades_manager()
        return config, exchange_inst, trader_inst, trades_manager_inst

    @staticmethod
    def stop(trader):
        trader.stop_order_manager()

    def test_get_reference_market(self):
        config, _, trader_inst, _ = self.init_default()
        assert TradesManager.get_reference_market(config) == DEFAULT_REFERENCE_MARKET

        config[CONFIG_TRADER][CONFIG_TRADER_REFERENCE_MARKET] = "ETH"
        assert TradesManager.get_reference_market(config) == "ETH"

        self.stop(trader_inst)

    def test_get_portfolio_current_value(self):
        pass

    def test_get_portfolio_origin_value(self):
        pass

    def test_get_profitability_without_update(self):
        pass

    def test_get_profitability(self):
        pass

    def test_add_new_trade_in_history(self):
        pass
