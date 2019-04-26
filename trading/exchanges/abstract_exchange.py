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
from abc import ABCMeta, abstractmethod
from config import ExchangeConstantsMarketPropertyColumns


class AbstractExchange:
    __metaclass__ = ABCMeta

    def __init__(self, config, exchange_type):
        self.config = config
        self.exchange_type = exchange_type
        self.name = self.exchange_type.__name__
        self.logger = get_logger(f"{self.__class__.__name__}[{self.name}]")
        self.trader = None

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
    async def get_balance(self):
        pass

    @abstractmethod
    async def get_symbol_prices(self, symbol, time_frame, limit=None, return_list=True):
        pass

    @abstractmethod
    async def get_order_book(self, symbol, limit=50):
        pass

    @abstractmethod
    async def get_recent_trades(self, symbol, limit=50):
        pass

    @abstractmethod
    async def get_price_ticker(self, symbol):
        pass

    @abstractmethod
    async def get_all_currencies_price_ticker(self):
        pass

    @abstractmethod
    async def get_order(self, order_id, symbol=None):
        pass

    @abstractmethod
    async def get_all_orders(self, symbol=None, since=None, limit=None):
        pass

    @abstractmethod
    async def get_open_orders(self, symbol=None, since=None, limit=None, force_rest=False):
        pass

    @abstractmethod
    async def get_closed_orders(self, symbol=None, since=None, limit=None):
        pass

    @abstractmethod
    async def get_my_recent_trades(self, symbol=None, since=None, limit=None):
        pass

    @abstractmethod
    async def cancel_order(self, order_id, symbol=None):
        pass

    @abstractmethod
    async def create_order(self, order_type, symbol, quantity, price=None, stop_price=None):
        pass

    @abstractmethod
    async def stop(self):
        pass

    @abstractmethod
    def get_market_status(self, symbol, price_example=None, with_fixer=True):
        pass

    @abstractmethod
    def get_uniform_timestamp(self, timestamp):
        pass

    @abstractmethod
    def get_fees(self, symbol):
        pass

    @abstractmethod
    def get_trade_fee(self, symbol, order_type, quantity, price,
                      taker_or_maker=ExchangeConstantsMarketPropertyColumns.TAKER.value):
        pass
