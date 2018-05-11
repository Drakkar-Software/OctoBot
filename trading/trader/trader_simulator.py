from config.cst import CONFIG_ENABLED_OPTION, CONFIG_SIMULATOR
from trading.trader.trader import Trader

""" TraderSimulator has a role of exchange response simulator
- During order creation / filling / canceling process"""


class TraderSimulator(Trader):
    def __init__(self, config, exchange):
        self.simulate = True
        super().__init__(config, exchange)

    @staticmethod
    def enabled(config):
        if config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION]:
            return True
        else:
            return False
