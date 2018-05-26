from config.cst import CONFIG_ENABLED_OPTION, CONFIG_SIMULATOR
from trading.trader.trader import Trader

""" TraderSimulator has a role of exchange response simulator
- During order creation / filling / canceling process"""


class TraderSimulator(Trader):
    def __init__(self, config, exchange, order_refresh_time=None):
        self.simulate = True
        super().__init__(config, exchange, order_refresh_time)

    @staticmethod
    def enabled(config):
        if config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION]:
            return True
        else:
            return False
