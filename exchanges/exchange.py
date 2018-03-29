from config.cst import *


class Exchange:
    def __init__(self, config):
        self.config = config

    # @return DataFrame of prices
    def get_symbol_prices(self, symbol, time_frame):
        pass

    @staticmethod
    def get_time_frame_enum():
        return TimeFrames
