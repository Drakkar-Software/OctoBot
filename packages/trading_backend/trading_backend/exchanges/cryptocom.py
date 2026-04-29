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


class CryptoCom(exchanges.Exchange):
    SPOT_ID = "OCTBT"
    MARGIN_ID = "OCTBT"
    FUTURE_ID = "OCTBT"
    IS_SPONSORING = True
    HEADER_SPOT_KEY = "agentSource"
    HEADER_FUTURE_KEY = "Referer"

    @classmethod
    def get_name(cls):
        return 'cryptocom'

    def get_orders_parameters(self, params=None) -> dict:
        if self._exchange.connector.client.options.get("broker", None) != self._get_id():
            self._exchange.connector.client.options["broker"] = self._get_id()
        return super().get_orders_parameters(params)
