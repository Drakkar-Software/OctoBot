import logging
from abc import ABCMeta, abstractmethod


class AbstractExchange:
    __metaclass__ = ABCMeta

    def __init__(self, config, exchange_type):
        self.config = config
        self.exchange_type = exchange_type
        self.name = self.exchange_type.__name__
        self.logger = logging.getLogger("{0} - {1}".format(self.__class__.__name__, self.name))

        self.exchange_manager = None

    def get_name(self):
        return self.name

    def get_config(self):
        return self.config

    def get_exchange_type(self):
        return self.exchange_type

    def get_exchange_manager(self):
        return self.exchange_manager

    @abstractmethod
    def get_balance(self):
        pass

    @abstractmethod
    def get_symbol_prices(self, symbol, time_frame, limit=None, data_frame=True):
        pass

    @abstractmethod
    def get_order_book(self, symbol, limit=50):
        pass

    @abstractmethod
    def get_recent_trades(self, symbol):
        pass

    @abstractmethod
    def get_market_price(self, symbol):
        pass

    @abstractmethod
    def get_price_ticker(self, symbol):
        pass

    @abstractmethod
    def get_all_currencies_price_ticker(self):
        pass

    @abstractmethod
    def get_order(self, order_id, symbol=None):
        pass

    @abstractmethod
    def get_all_orders(self, symbol=None, since=None, limit=None):
        pass

    @abstractmethod
    def get_open_orders(self, symbol=None, since=None, limit=None, force_rest=False):
        pass

    @abstractmethod
    def get_closed_orders(self, symbol=None, since=None, limit=None):
        pass

    @abstractmethod
    def get_my_recent_trades(self, symbol=None, since=None, limit=None):
        pass

    @abstractmethod
    def cancel_order(self, order_id, symbol=None):
        pass

    @abstractmethod
    def create_order(self, order_type, symbol, quantity, price=None, stop_price=None):
        pass

    @abstractmethod
    def get_market_status(self, symbol):
        pass

    @abstractmethod
    def get_uniform_timestamp(self, timestamp):
        pass
