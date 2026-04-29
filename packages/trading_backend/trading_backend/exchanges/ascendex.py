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


class Ascendex(exchanges.Exchange):
    SPOT_ID = "OctoBot"
    MARGIN_ID = "OctoBot"
    FUTURE_ID = "OctoBot"
    IS_SPONSORING = True

    @classmethod
    def get_name(cls):
        return 'ascendex'

    def _generate_order_id(self):
        new_id = "".join(self._exchange.connector.client.uuid().split("-"))
        return f"{self._get_id()}{new_id[len(self._get_id()):]}"

    def get_orders_parameters(self, params=None) -> dict:
        # no ccxt broker id automation
        params = super().get_orders_parameters(params)
        params.update({'id': self._generate_order_id()})
        return params
