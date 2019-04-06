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

import requests
from binance.client import Client, BinanceAPIException
from binance.websockets import BinanceSocketManager

from config import *
from config.config import decrypt
from trading.exchanges.websockets_exchanges.user_websocket.user_websocket import UserWebSocket


class BinanceWebSocketClient(UserWebSocket):
    _USER_SOCKET_NAME = "user"
    _STATUSES = {
        'NEW': 'open',
        'PARTIALLY_FILLED': 'open',
        'FILLED': 'closed',
        'CANCELED': 'canceled'
    }

    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)
        try:
            if self.exchange_manager.should_decrypt_token(self.logger):
                self.client = Client(decrypt(self.config[CONFIG_EXCHANGES][self.name][CONFIG_EXCHANGE_KEY]),
                                     decrypt(self.config[CONFIG_EXCHANGES][self.name][CONFIG_EXCHANGE_SECRET]))
            else:
                self.client = Client("", "")
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Impossible to initialize websocket: {e}")
        except Exception as e:
            self.exchange_manager.handle_token_error(e, self.logger)
            try:
                self.client = Client("", "")
            except requests.exceptions.ConnectionError as e:
                self.logger.error(f"Impossible to initialize websocket: {e}")

        self.socket_manager = None
        self.open_sockets_keys = {}

    @staticmethod
    def get_websocket_client(config, exchange_manager):
        ws_client = BinanceWebSocketClient(config, exchange_manager)
        ws_client.socket_manager = BinanceSocketManager(ws_client.client)
        return ws_client

    def init_web_sockets(self, time_frames, trader_pairs):
        try:
            if self.exchange_manager.need_user_stream():
                self._init_user_socket()
        except BinanceAPIException as e:
            self.logger.error(f"error when connecting to binance web sockets: {e}")

    def _init_user_socket(self):
        connection_key = self.socket_manager.start_user_socket(self.user_callback)
        self.open_sockets_keys[self._USER_SOCKET_NAME] = connection_key

    def start_sockets(self):
        if self.socket_manager:
            self.socket_manager.start()

    def close_and_restart_sockets(self):
        for socket_key in self.open_sockets_keys.values():
            self.socket_manager.stop_socket(socket_key)
        self.socket_manager.close()
        self.logger.info(f"{len(self.open_sockets_keys)} web socket(s) restarted")

    def stop_sockets(self):
        if self.socket_manager:
            self.socket_manager.close()

    def get_socket_manager(self):
        return self.socket_manager

    @classmethod
    def get_name(cls):
        return "binance"

    @classmethod
    def has_name(cls, name: str):
        if name == cls.get_name():
            return True
        return False

    def handles_balance(self) -> bool:
        return True

    def handles_orders(self) -> bool:
        return True

    @staticmethod
    def parse_order_status(status):
        return BinanceWebSocketClient._STATUSES[status] if status in BinanceWebSocketClient._STATUSES \
            else status.lower()

    def convert_into_ccxt_order(self, order):
        status = self.safe_value(order, 'X')
        if status is not None:
            status = self.parse_order_status(status)
        price = self.safe_float(order, "p")
        amount = self.safe_float(order, "q")
        filled = self.safe_float(order, "z", 0.0)
        cost = None
        remaining = None
        fee = {
            FeePropertyColumns.COST.value: self.safe_float(order, "n"),
            FeePropertyColumns.CURRENCY.value: self.safe_string(order, "N", "?"),
        }
        if filled is not None and filled > 0:
            if amount is not None:
                remaining = max(amount - filled, 0.0)
            if price is not None and price > 0:
                cost = price * filled
            else:
                # market order case => estimate price and cost using last_price
                price = self.safe_float(order, "L", 0.0)
                cost = price * filled
        return {
            ExchangeConstantsOrderColumns.INFO.value: order,
            ExchangeConstantsOrderColumns.ID.value: self.safe_string(order, "i"),
            ExchangeConstantsOrderColumns.TIMESTAMP.value: order["T"],
            ExchangeConstantsOrderColumns.DATETIME.value: self.iso8601(order["T"]),
            ExchangeConstantsOrderColumns.LAST_TRADE_TIMESTAMP.value: None,
            ExchangeConstantsOrderColumns.SYMBOL.value: self._adapt_symbol(self.safe_string(order, "s")),
            ExchangeConstantsOrderColumns.TYPE.value: self.safe_lower_string(order, "o"),
            ExchangeConstantsOrderColumns.SIDE.value: self.safe_lower_string(order, "S"),
            ExchangeConstantsOrderColumns.PRICE.value: price,
            ExchangeConstantsOrderColumns.AMOUNT.value: amount,
            ExchangeConstantsOrderColumns.COST.value: cost,
            ExchangeConstantsOrderColumns.FILLED.value: filled,
            ExchangeConstantsOrderColumns.REMAINING.value: remaining,
            ExchangeConstantsOrderColumns.STATUS.value: status,
            ExchangeConstantsOrderColumns.FEE.value: fee,
        }

    def user_callback(self, msg):
        try:
            if msg["e"] == "outboundAccountInfo":
                self._update_portfolio(msg)
            elif msg["e"] == "executionReport":
                self._update_order(msg)
            elif msg['e'] == 'error':
                self.logger.error(f"error in web socket user_callback ({msg['m']}), calling restart_sockets()")
                self.close_and_restart_sockets()
        except Exception as e:
            self.logger.exception(e)
            self.logger.error(f"error: {e}, restarting calling restart_sockets()")
            self.close_and_restart_sockets()

    def _update_portfolio(self, msg):
        if self.exchange_manager.get_personal_data().get_portfolio_is_initialized():
            for currency in msg['B']:
                free = float(currency['f'])
                locked = float(currency['l'])
                total = free + locked
                self.exchange_manager.get_personal_data().update_portfolio(currency['a'], total, free, locked)
