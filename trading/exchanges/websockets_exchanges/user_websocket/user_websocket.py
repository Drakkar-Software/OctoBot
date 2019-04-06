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
from trading.exchanges.websockets_exchanges import AbstractWebSocket


class UserWebSocket(AbstractWebSocket):

    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)

    # Abstract methods
    @classmethod
    def get_name(cls):
        raise NotImplementedError("get_name not implemented")

    @classmethod
    def has_name(cls, name: str) -> bool:
        raise NotImplementedError("has_name not implemented")

    def convert_into_ccxt_order(self, order):
        raise NotImplementedError("convert_into_ccxt_order not implemented")

    def start_sockets(self):
        raise NotImplementedError("start_sockets not implemented")

    def stop_sockets(self):
        raise NotImplementedError("stop_sockets not implemented")

    @staticmethod
    def get_websocket_client(config, exchange_manager):
        raise NotImplementedError("get_websocket_client not implemented")

    def init_web_sockets(self, time_frames, trader_pairs):
        raise NotImplementedError("init_web_sockets not implemented")

    def close_and_restart_sockets(self):
        raise NotImplementedError("close_and_restart_sockets not implemented")

    @staticmethod
    def parse_order_status(status):
        raise NotImplementedError("parse_order_status not implemented")

    def handles_balance(self) -> bool:
        raise NotImplementedError("handles_balance not implemented")

    def handles_orders(self) -> bool:
        raise NotImplementedError("handles_orders not implemented")

    # ============== ccxt adaptation methods ==============
    def init_ccxt_order_from_other_source(self, ccxt_order):
        if self.exchange_manager.get_personal_data().get_orders_are_initialized():
            self.exchange_manager.get_personal_data().upsert_order(ccxt_order["id"], ccxt_order)

    def _update_order(self, msg):
        if self.exchange_manager.get_personal_data().get_orders_are_initialized():
            ccxt_order = self.convert_into_ccxt_order(msg)
            self.exchange_manager.get_personal_data().upsert_order(ccxt_order["id"], ccxt_order)
