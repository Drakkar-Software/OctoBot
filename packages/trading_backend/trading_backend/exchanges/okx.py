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
import trading_backend.enums


class OKX(exchanges.Exchange):
    SPOT_ID = "c812bf5944b749BC"
    MARGIN_ID = "c812bf5944b749BC"
    FUTURE_ID = "c812bf5944b749BC"
    IS_SPONSORING = True

    @classmethod
    def get_name(cls):
        return 'okx'

    async def _get_api_key_rights(self) -> list[trading_backend.enums.APIKeyRights]:
        accounts = await self._exchange.connector.client.fetch_accounts()
        if not accounts:
            return []
        restrictions = accounts[0]["info"]["perm"].split(",")
        rights = []
        if "read_only" in restrictions:
            rights.append(trading_backend.enums.APIKeyRights.READING)
        if "trade" in restrictions:
            rights.append(trading_backend.enums.APIKeyRights.SPOT_TRADING)
            rights.append(trading_backend.enums.APIKeyRights.MARGIN_TRADING)
            rights.append(trading_backend.enums.APIKeyRights.FUTURES_TRADING)
        if "withdraw" in restrictions:
            rights.append(trading_backend.enums.APIKeyRights.WITHDRAWALS)
        return rights

    def get_orders_parameters(self, params=None) -> dict:
        if self._exchange.connector.client.options.get("brokerId", "") != self._get_id():
            self._exchange.connector.client.options["brokerId"] = self._get_id()
        return super().get_orders_parameters(params)
