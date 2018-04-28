from config.cst import *


class Backtesting:
    def __init__(self, config):
        self.config = config

    def end(self):
        # TODO : temp
        raise Exception("End of simulation")

    @staticmethod
    def enabled(config):
        return CONFIG_BACKTESTING in config and config[CONFIG_BACKTESTING][CONFIG_ENABLED_OPTION]
