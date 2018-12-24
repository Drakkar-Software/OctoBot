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

import time

from config import ExchangeConstantsMarketPropertyColumns
from trading import AbstractExchange
from trading.exchanges.exchange_personal_data import ExchangePersonalData
from trading.exchanges.exchange_symbol_data import SymbolData

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

    def get_symbol_data(self, symbol):
        if symbol not in self.symbols_data:
            self.symbols_data[symbol] = SymbolData(symbol)
        return self.symbols_data[symbol]

    # total (free + used), by currency
    def get_balance(self):
        if not self._web_socket_available() or not self.exchange_personal_data.get_portfolio_is_initialized():
            if not self.exchange_personal_data.get_portfolio_is_initialized():
                self.exchange_personal_data.init_portfolio()

            self.exchange.get_balance()

        return self.exchange_personal_data.get_portfolio()

    def get_symbol_prices(self, symbol, time_frame, limit=None, return_list=True):
        symbol_data = self.get_symbol_data(symbol)
        from_web_socket = False
        if not self._web_socket_available() or not symbol_data.candles_are_initialized(time_frame):
            self.exchange.get_symbol_prices(symbol=symbol, time_frame=time_frame, limit=limit)
        else:
            from_web_socket = True

        symbol_prices = symbol_data.get_symbol_prices(time_frame, limit, return_list)

        if from_web_socket:
            # web socket: ensure data are the most recent one otherwise restart web socket
            if not symbol_data.ensure_data_validity(time_frame):
                self._handle_web_socket_reset()
                return self.get_symbol_prices(symbol, time_frame, limit, return_list)

        return symbol_prices

    def _handle_web_socket_reset(self):
        # first check if reset is not already running
        if self.resetting_web_socket:
            # if true: a reset is being processed in another thread, wait for it to be over and recall method
            while self.resetting_web_socket:
                time.sleep(0.01)
        else:
            self.resetting_web_socket = True
            # otherwise: reset web socket and recall method
            self.logger.warning("web socket seems to be disconnected, trying to restart it")
            try:
                self.get_exchange_manager().reset_websocket_exchange()
            except Exception as e:
                self.logger.error("Error when trying to restart web socket")
                self.logger.exception(e)
            finally:
                self.resetting_web_socket = False

    # return bid and asks on each side of the order book stack
    # careful here => can be for binance limit > 100 has a 5 weight and > 500 a 10 weight !
    def get_order_book(self, symbol, limit=50):
        if not self._web_socket_available():
            self.exchange.get_order_book(symbol, limit)

        return self.get_symbol_data(symbol).get_symbol_order_book(limit)

    def get_recent_trades(self, symbol, limit=50):
        symbol_data = self.get_symbol_data(symbol)

        if not self._web_socket_available() or not symbol_data.recent_trades_are_initialized():
            if not self._web_socket_available() or \
                    (self._web_socket_available() and self.exchange_web_socket.handles_recent_trades()):
                symbol_data.init_recent_trades()
            self.exchange.get_recent_trades(symbol=symbol, limit=limit)

        return symbol_data.get_symbol_recent_trades(limit)

    # A price ticker contains statistics for a particular market/symbol for some period of time in recent past (24h)
    def get_price_ticker(self, symbol):
        symbol_data = self.get_symbol_data(symbol)

        if not self._web_socket_available() or not symbol_data.price_ticker_is_initialized():
            self.exchange.get_price_ticker(symbol=symbol)

        return symbol_data.get_symbol_ticker()

    def get_all_currencies_price_ticker(self):
        return self.exchange.get_all_currencies_price_ticker()

    def get_market_status(self, symbol, price=None):
        return self.exchange.get_market_status(symbol, price)

    # ORDERS
    def get_order(self, order_id, symbol=None):
        if not self._web_socket_available() or not self.exchange_personal_data.get_orders_are_initialized():
            self.exchange.get_order(order_id, symbol=symbol)

        return self.exchange_personal_data.get_order(order_id)

    def get_all_orders(self, symbol=None, since=None, limit=None):
        if not self._web_socket_available() or not self.exchange_personal_data.get_orders_are_initialized():
            if not self.exchange_personal_data.get_orders_are_initialized():
                self.exchange_personal_data.init_orders()

            self.exchange.get_all_orders(symbol=symbol,
                                         since=since,
                                         limit=limit)

        return self.exchange_personal_data.get_all_orders(symbol, since, limit)

    def get_open_orders(self, symbol=None, since=None, limit=None, force_rest=False):
        if not self._web_socket_available() \
                or not self.exchange_personal_data.get_orders_are_initialized() \
                or force_rest:
            self.exchange.get_open_orders(symbol=symbol,
                                          since=since,
                                          limit=limit)

        return self.exchange_personal_data.get_open_orders(symbol, since, limit)

    def get_closed_orders(self, symbol=None, since=None, limit=None):
        if not self._web_socket_available() or not self.exchange_personal_data.get_orders_are_initialized():
            self.exchange.get_closed_orders(symbol=symbol,
                                            since=since,
                                            limit=limit)

        return self.exchange_personal_data.get_closed_orders(symbol, since, limit)

    def get_my_recent_trades(self, symbol=None, since=None, limit=None):
        if not self._web_socket_available():
            self.exchange.get_my_recent_trades(symbol=symbol,
                                               since=since,
                                               limit=limit)

        return self.exchange_personal_data.get_my_recent_trades(symbol=symbol,
                                                                since=since,
                                                                limit=limit)

    def cancel_order(self, order_id, symbol=None):
        return self.exchange.cancel_order(symbol=symbol,
                                          order_id=order_id)

    def create_order(self, order_type, symbol, quantity, price=None, stop_price=None):
        return self.exchange.create_order(symbol=symbol,
                                          order_type=order_type,
                                          quantity=quantity,
                                          price=price,
                                          stop_price=stop_price)

    def stop(self):
        if self._web_socket_available():
            self.exchange_web_socket.stop_sockets()

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
