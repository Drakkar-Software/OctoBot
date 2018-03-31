from abc import *


class Exchange:
    __metaclass__ = ABCMeta

    def __init__(self, config):
        self.config = config
        self.symbol_list = []

    # @return DataFrame of prices
    @abstractmethod
    def get_symbol_prices(self, symbol, time_frame):
        raise NotImplementedError("Get_symbol_prices not implemented")

    @abstractmethod
    def get_symbol_list(self):
        raise NotImplementedError("Get_symbol_list not implemented")

    @abstractmethod
    def symbol_exists(self, symbol):
        raise NotImplementedError("Symbol_exists not implemented")

    @staticmethod
    @abstractmethod
    def get_time_frame_enum():
        raise NotImplementedError("Get_time_frame_enum not implemented")
