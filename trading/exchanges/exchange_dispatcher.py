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

import asyncio
from copy import copy
from ccxt.async_support import BaseError

from config import ExchangeConstantsMarketPropertyColumns, DEFAULT_REST_RETRY_COUNT, EXCHANGE_ERROR_SLEEPING_TIME
from trading import AbstractExchange
from trading.exchanges.exchange_personal_data import ExchangePersonalData
from trading.exchanges.exchange_symbol_data import SymbolData
from trading.exchanges.exchange_exceptions import MissingOrderException

"""
This class supervise exchange call by :
- Storing data through ExchangePersonalData and ExchangeSymbolData
- Use web socket calls as much as possible (if available else use REST exchange with ccxt lib)
"""


class ExchangeDispatcher(AbstractExchange):
    def __init__(self, config, exchange_type, exchange, exchange_web_socket):
        super().__init__(config, exchange_type)

        self.exchange = exchange
        self.exchange_web_socket = exchange_web_socket
        self.symbols_data = None

        self.resetting_web_socket = False

        self.reset_symbols_data()
        self.exchange_personal_data = ExchangePersonalData()

        self.logger.info(f"online with REST api{' and web socket api' if self.exchange_web_socket else ''}")

    def reset_symbols_data(self):
        self.symbols_data = {}

    def reset_exchange_personal_data(self):
        self.exchange_personal_data = ExchangePersonalData()

    def _web_socket_available(self):
        return self.exchange_web_socket

    def is_web_socket_available(self) -> bool:
        return self._web_socket_available()

    def get_name(self):
        return self.exchange.get_name()

    def get_exchange_manager(self):
        return self.exchange.get_exchange_manager()

    def get_exchange(self):
        return self.exchange

    def get_exchange_personal_data(self):
        return self.exchange_personal_data

    # used to retry a specific method for a limited amount of attempts in case the expected exception occurs
    async def execute_request_with_retry(self, coroutine, retry_count=DEFAULT_REST_RETRY_COUNT,
                                         retry_exception=BaseError):
        got_results = False
        attempt = 0
        # extract method name
        method_name = coroutine.__qualname__.split(".")[-1]
        # copy not to alter original coroutine
        method_args = copy(coroutine.cr_frame.f_locals)
        # need to remove self attr to be able to find method with getattr(self, ...)
        # and then give it the original coroutine's arguements
        method_args.pop("self")
        result = None
        while not got_results and attempt < retry_count:
            try:
                attempt += 1
                if attempt == 1:
                    result = await coroutine
                else:
                    # 2nd time or more: await a new identical coroutine (can't await the same coroutine twice)
                    result = await getattr(self, method_name)(**method_args)
                got_results = True
            except retry_exception as e:
                if attempt < DEFAULT_REST_RETRY_COUNT:
                    sleeping_time = attempt*EXCHANGE_ERROR_SLEEPING_TIME
                    self.logger.warning(f"Failed to execute: {method_name} ({e}) retrying in {sleeping_time} seconds.")
                    # maybe just a short downtime, retry a bit later
                    await asyncio.sleep(sleeping_time)
                else:
                    self.logger.error(f"Failed to execute: {method_name} ({e}), after {retry_count} attempts.")
                    # real problem: raise error
                    raise e
        return result

    def get_symbol_data(self, symbol):
        if symbol not in self.symbols_data:
            self.symbols_data[symbol] = SymbolData(symbol)
        return self.symbols_data[symbol]

    # total (free + used), by currency
    async def get_balance(self):
        if not self._web_socket_available() or not self.exchange_personal_data.get_portfolio_is_initialized():
            if not self.exchange_personal_data.get_portfolio_is_initialized():
                self.exchange_personal_data.init_portfolio()

            await self.exchange.get_balance()

        return self.exchange_personal_data.get_portfolio()

    async def get_symbol_prices(self, symbol, time_frame, limit=None, return_list=True):
        symbol_data = self.get_symbol_data(symbol)
        from_web_socket = False
        if not self._web_socket_available() or not symbol_data.candles_are_initialized(time_frame):
            await self.exchange.get_symbol_prices(symbol=symbol, time_frame=time_frame, limit=limit)
        else:
            from_web_socket = True

        symbol_prices = symbol_data.get_symbol_prices(time_frame, limit, return_list)

        if from_web_socket:
            # web socket: ensure data are the most recent one otherwise restart web socket
            if not symbol_data.ensure_data_validity(time_frame):
                message = "Web socket seems to be disconnected, trying to restart it"
                await self._handle_web_socket_reset(message)
                return await self.get_symbol_prices(symbol, time_frame, limit, return_list)

        return symbol_prices

    async def reset_web_sockets_if_any(self):
        if self._web_socket_available():
            await self._handle_web_socket_reset("Resetting web sockets")

    async def _handle_web_socket_reset(self, message):
        # first check if reset is not already running
        if self.resetting_web_socket:
            # if true: a reset is being processed in another task, wait for it to be over and recall method
            while self.resetting_web_socket:
                await asyncio.sleep(0.01)
        else:
            self.resetting_web_socket = True
            # otherwise: reset web socket and recall method
            self.logger.warning(message)
            try:
                self.get_exchange_manager().reset_websocket_exchange()
            except Exception as e:
                self.logger.error("Error when trying to restart web socket")
                self.logger.exception(e)
            finally:
                self.resetting_web_socket = False

    # return bid and asks on each side of the order book stack
    # careful here => can be for binance limit > 100 has a 5 weight and > 500 a 10 weight !
    async def get_order_book(self, symbol, limit=50):
        symbol_data = self.get_symbol_data(symbol)

        if not self._web_socket_available() or not symbol_data.order_book_is_initialized():
            if not self._web_socket_available() or \
                    (self._web_socket_available() and self.exchange_web_socket.handles_order_book()):
                symbol_data.init_order_book()
            await self.exchange.get_order_book(symbol=symbol, limit=limit)

        return symbol_data.get_symbol_order_book()

    async def get_recent_trades(self, symbol, limit=50):
        symbol_data = self.get_symbol_data(symbol)

        if not self._web_socket_available() or not symbol_data.recent_trades_are_initialized():
            if not self._web_socket_available() or \
                    (self._web_socket_available() and self.exchange_web_socket.handles_recent_trades()):
                symbol_data.init_recent_trades()
            await self.exchange.get_recent_trades(symbol=symbol, limit=limit)

        return symbol_data.get_symbol_recent_trades()

    # A price ticker contains statistics for a particular market/symbol for some period of time in recent past (24h)
    async def get_price_ticker(self, symbol):
        symbol_data = self.get_symbol_data(symbol)

        if not self._web_socket_available() or not symbol_data.price_ticker_is_initialized():
            await self.exchange.get_price_ticker(symbol=symbol)

        return symbol_data.get_symbol_ticker()

    async def get_all_currencies_price_ticker(self):
        return await self.exchange.get_all_currencies_price_ticker()

    def get_market_status(self, symbol, price_example=None, with_fixer=True):
        return self.exchange.get_market_status(symbol, price_example, with_fixer)

    # ORDERS
    async def get_order(self, order_id, symbol=None):
        if not self._web_socket_available() \
                or not self.exchange_personal_data.get_orders_are_initialized()\
                or not self.exchange_personal_data.has_order(order_id):
            await self.exchange.get_order(order_id, symbol=symbol)

        if self.exchange_personal_data.has_order(order_id):
            return self.exchange_personal_data.get_order(order_id)
        else:
            raise MissingOrderException(order_id)

    async def get_all_orders(self, symbol=None, since=None, limit=None):
        if not self._web_socket_available() or not self.exchange_personal_data.get_orders_are_initialized():
            if not self.exchange_personal_data.get_orders_are_initialized():
                self.exchange_personal_data.init_orders()

            await self.exchange.get_all_orders(symbol=symbol,
                                               since=since,
                                               limit=limit)

        return self.exchange_personal_data.get_all_orders(symbol, since, limit)

    async def get_open_orders(self, symbol=None, since=None, limit=None, force_rest=False):
        if not self._web_socket_available() \
                or not self.exchange_personal_data.get_orders_are_initialized() \
                or force_rest:
            await self.exchange.get_open_orders(symbol=symbol,
                                                since=since,
                                                limit=limit)

        return self.exchange_personal_data.get_open_orders(symbol, since, limit)

    async def get_closed_orders(self, symbol=None, since=None, limit=None):
        if not self._web_socket_available() or not self.exchange_personal_data.get_orders_are_initialized():
            await self.exchange.get_closed_orders(symbol=symbol,
                                                  since=since,
                                                  limit=limit)

        return self.exchange_personal_data.get_closed_orders(symbol, since, limit)

    async def get_my_recent_trades(self, symbol=None, since=None, limit=None):
        if not self._web_socket_available():
            await self.exchange.get_my_recent_trades(symbol=symbol,
                                                     since=since,
                                                     limit=limit)

        return self.exchange_personal_data.get_my_recent_trades(symbol=symbol,
                                                                since=since,
                                                                limit=limit)

    async def cancel_order(self, order_id, symbol=None):
        return await self.exchange.cancel_order(symbol=symbol,
                                                order_id=order_id)

    async def create_order(self, order_type, symbol, quantity, price=None, stop_price=None):
        return await self.exchange.create_order(symbol=symbol,
                                                order_type=order_type,
                                                quantity=quantity,
                                                price=price,
                                                stop_price=stop_price)

    async def stop(self):
        if self._web_socket_available():
            self.exchange_web_socket.stop_sockets()
        await self.exchange.stop()

    def get_uniform_timestamp(self, timestamp):
        return self.exchange.get_uniform_timestamp(timestamp)

    # returns {
    #     'type': takerOrMaker,
    #     'currency': 'BTC', // the unified fee currency code
    #     'rate': percentage, // the fee rate, 0.05% = 0.0005, 1% = 0.01, ...
    #     'cost': feePaid, // the fee cost (amount * fee rate)
    # }
    # equivalent to: {
    #     FeePropertyColumns.TYPE.value: takerOrMaker,
    #     FeePropertyColumns.CURRENCY.value: 'BTC',
    #     FeePropertyColumns.RATE.value: percentage,
    #     FeePropertyColumns.COST.value: feePaid
    # }
    def get_trade_fee(self, symbol, order_type, quantity, price,
                      taker_or_maker=ExchangeConstantsMarketPropertyColumns.TAKER.value):
        return self.exchange.get_trade_fee(
            symbol=symbol,
            order_type=order_type,
            quantity=quantity,
            price=price,
            taker_or_maker=taker_or_maker
        )

    # returns {
    #       "taker": taker_fee,
    #       "maker": maker_fee,
    #       "withdraw": withdraw_fee
    # }
    def get_fees(self, symbol):
        return self.exchange.get_fees(symbol=symbol)
