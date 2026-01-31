#  Drakkar-Software trading-backend
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
import trading_backend.exchanges as exchanges


class HTX(exchanges.Exchange):
    SPOT_ID = "AAc4ccb049"
    MARGIN_ID = ""
    FUTURE_ID = "AAc4ccb049"  # TODO check integration method
    IS_SPONSORING = True

    @classmethod
    def get_name(cls):
        return 'htx'

    def get_orders_parameters(self, params=None) -> dict:
        if "broker" not in self._exchange.connector.client.options:
            self._exchange.connector.client.options["broker"] = {}
        options_broker = self._exchange.connector.client.options["broker"]
        if options_broker.get("id", None) != self._get_id():
            self._exchange.connector.client.options["broker"]["id"] = self._get_id()
        return super().get_orders_parameters(params)
