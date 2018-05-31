from config.cst import CONFIG_ENABLED_OPTION, CONFIG_SIMULATOR, SIMULATOR_TRADER_STR
from trading.trader.trader import Trader

""" TraderSimulator has a role of exchange response simulator
- During order creation / filling / canceling process"""


class TraderSimulator(Trader):
    def __init__(self, config, exchange, order_refresh_time=None):
        self.simulate = True
        super().__init__(config, exchange, order_refresh_time)

        self.trader_type_str = SIMULATOR_TRADER_STR

    @staticmethod
    def enabled(config):
        return config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION]
