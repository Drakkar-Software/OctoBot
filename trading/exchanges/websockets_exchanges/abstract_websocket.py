#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

from tools.logging.logging_util import get_logger
from abc import *

from ccxt.base.exchange import Exchange as ccxtExchange

from config import TimeFrames


class AbstractWebSocket:

    def __init__(self, config, exchange_manager):
        self.config = config
        self.exchange_manager = exchange_manager
        self.client = None
        self.name = self.get_name()
        self.logger = get_logger(f"WebSocket - {self.name}")

    # Abstract methods
    @classmethod
    @abstractmethod
    def get_name(cls):
        raise NotImplementedError("get_name not implemented")

    @abstractmethod
    def convert_into_ccxt_order(self, order):
        raise NotImplementedError("convert_into_ccxt_order not implemented")

    @abstractmethod
    def convert_into_ccxt_ticker(self, ticker):
        raise NotImplementedError("convert_into_ccxt_ticker not implemented")

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

    @abstractmethod
    def close_and_restart_sockets(self):
        raise NotImplementedError("close_and_restart_sockets not implemented")

    # ============== ccxt adaptation methods ==============
    def init_ccxt_order_from_other_source(self, ccxt_order):
        if self.exchange_manager.get_personal_data().get_orders_are_initialized():
            self.exchange_manager.get_personal_data().upsert_order(ccxt_order["id"], ccxt_order)

    def _update_order(self, msg):
        if self.exchange_manager.get_personal_data().get_orders_are_initialized():
            ccxt_order = self.convert_into_ccxt_order(msg)
            self.exchange_manager.get_personal_data().upsert_order(ccxt_order["id"], ccxt_order)

    def _parse_symbol_from_ccxt(self, symbol):
        try:
            return self.exchange_manager.get_ccxt_exchange().get_client().markets_by_id[symbol]['symbol']
        except Exception as e:
            self.logger.error(f"Can't parse {symbol} from ccxt exchange")
            self.logger.exception(e)

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
    def safe_integer(dictionary, key, default_value=None):
        return ccxtExchange.safe_integer(dictionary, key, default_value)

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
        return self.exchange_manager.get_personal_data()
