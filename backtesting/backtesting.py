import time

from config.cst import *


class Backtesting:
    def __init__(self, config):
        self.config = config
        self.begin_time = time.time()

    def end(self):
        # TODO : temp
        raise Exception("End of simulation in {0} sec".format(time.time() - self.begin_time))

    @staticmethod
    def enabled(config):
        return CONFIG_BACKTESTING in config and config[CONFIG_BACKTESTING][CONFIG_ENABLED_OPTION]
