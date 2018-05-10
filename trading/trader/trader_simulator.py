from config.cst import CONFIG_ENABLED_OPTION
from trading.trader.trader import Trader

""" TraderSimulator has a role of exchange response simulator
- During order creation / filling / canceling process"""


class TraderSimulator(Trader):
    def __init__(self, config, exchange):
        self.simulate = True
        super().__init__(config, exchange)

    def enabled(self):
        if self.config["simulator"][CONFIG_ENABLED_OPTION]:
            return True
        else:
            return False
