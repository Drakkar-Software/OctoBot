import logging
from abc import *

from ccxt.base.exchange import Exchange as ccxtExchange

from config.cst import TimeFrames


class AbstractWebSocket:

    def __init__(self, config, exchange_manager):
        self.config = config
        self.exchange_manager = exchange_manager
        self.client = None
        self.name = self.get_name()
        self.logger = logging.getLogger(self.name)

    # Abstract methods
    @classmethod
    @abstractmethod
    def get_name(cls):
        raise NotImplementedError("get_name not implemented")

    @staticmethod
    @abstractmethod
    def convert_into_ccxt_order(order):
        raise NotImplementedError("convert_into_ccxt_order not implemented")

    @abstractmethod
    def start_sockets(self):
        raise NotImplementedError("start_sockets not implemented")

    @abstractmethod
    def stop_sockets(self):
        raise NotImplementedError("stop_sockets not implemented")

    @staticmethod
    @abstractmethod
    def get_websocket_client(config, exchange_manager):
        raise NotImplementedError("get_websocket_client not implemented")

    @abstractmethod
    def init_web_sockets(self, time_frames, trader_pairs):
        raise NotImplementedError("init_web_sockets not implemented")

    # ============== ccxt adaptation methods ==============
    def init_ccxt_order_from_other_source(self, ccxt_order):
        self.exchange_manager.get_exchange_personal_data().upsert_order(ccxt_order["id"], ccxt_order)

    def _update_order(self, msg):
        ccxt_order = self.convert_into_ccxt_order(msg)
        self.exchange_manager.get_exchange_personal_data().upsert_order(ccxt_order["id"], ccxt_order)

    @staticmethod
    @abstractmethod
    def parse_order_status(status):
        raise NotImplementedError("parse_order_status not implemented")

    @staticmethod
    def safe_lower_string(dictionary, key, default_value=None):
        value = AbstractWebSocket.safe_string(dictionary, key, default_value)
        if value is not None:
            value = value.lower()
        return value

    @staticmethod
    def safe_string(dictionary, key, default_value=None):
        return ccxtExchange.safe_string(dictionary, key, default_value)

    @staticmethod
    def safe_float(dictionary, key, default_value=None):
        return ccxtExchange.safe_float(dictionary, key, default_value)

    @staticmethod
    def safe_value(dictionary, key, default_value=None):
        return ccxtExchange.safe_value(dictionary, key, default_value)

    @staticmethod
    def iso8601(value):
        return ccxtExchange.iso8601(value)

    @classmethod
    @abstractmethod
    def handles_recent_trades(cls):
        raise NotImplementedError("handles_recent_trades not implemented")

    @classmethod
    @abstractmethod
    def handles_order_book(cls):
        raise NotImplementedError("handles_order_book not implemented")

    @classmethod
    @abstractmethod
    def handles_price_ticker(cls):
        raise NotImplementedError("handles_price_ticker not implemented")

    @staticmethod
    def _adapt_symbol(symbol):
        return symbol

    @staticmethod
    def _convert_time_frame(str_time_frame):
        return TimeFrames(str_time_frame)

    def get_symbol_data(self, symbol):
        return self.exchange_manager.get_symbol_data(self._adapt_symbol(symbol))

    def get_personal_data(self):
        return self.exchange_manager.get_exchange_personal_data()
