import ccxt

from trading.exchanges.exchange_manager import ExchangeManager
from tests.test_utils.config import load_test_config
from trading.trader.trader import Trader


class TestOrdersManagers:
    @staticmethod
    def init_default():
        config = load_test_config()
        exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
        exchange_inst = exchange_manager.get_exchange()
        trader_inst = Trader(config, exchange_inst, 1)
        order_manager_inst = trader_inst.get_order_manager()
        return config, exchange_inst, trader_inst, order_manager_inst

    @staticmethod
    def stop(trader):
        trader.stop_order_manager()

    def test_add_order_to_list(self):
        pass

    def test_remove_order_from_list(self):
        pass

    def test_update_last_symbol_list(self):
        pass

    def test_update_last_symbol_prices(self):
        pass

    def test_in_run(self):
        pass
