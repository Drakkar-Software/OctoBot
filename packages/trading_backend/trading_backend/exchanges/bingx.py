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
import ccxt

import trading_backend.exchanges as exchanges
import trading_backend.enums


class Bingx(exchanges.Exchange):
    SPOT_ID = "OctoBot"
    FUTURE_ID = "OctoBot"
    IS_SPONSORING = True

    @classmethod
    def get_name(cls):
        return 'bingx'

    async def _inner_cancel_order(self):
        # use client api to avoid any ccxt call wrapping and error handling
        try:
            await self._exchange.connector.client.cancel_order("12345", symbol=self._get_symbol())
        except ccxt.ExchangeError as err:
            # ('bingx {"code":100413,"msg":"Incorrect apiKey","timestamp":1718551786654}',)
            if "Incorrect apiKey".lower() in str(err).lower():
                # error is not caught by ccxt as such
                raise ccxt.AuthenticationError(f"Invalid key format ({err})")
            raise

    async def _get_api_key_rights(self) -> list[trading_backend.enums.APIKeyRights]:
        # It is currently impossible to fetch api key permissions: try to cancel an imaginary order,
        # if a permission error is raised instead of a cancel fail, then trading permissions are missing.
        # updated: 24/01/2024
        return await self._get_api_key_rights_using_order()

        # todo use this when available (current issue is that ccxt bingx sign() requires "v1" to be the second value of
        # the path and it's the 1st in /openApi/v1/account/apiRestrictions which crashes in  implode_hostname

        # https://bingx-api.github.io/docs/#/en-us/common/permission-interface.html#Query%20user%20API%20Key%20permissions
        # GET /openApi/v1/account/apiRestrictions
        # not on ccxt yet
        # restrictions = await self._exchange.connector.client.accountV1PrivateGetapiRestrictions(self._exchange.connector.client)
        # rights = []
        # if restrictions.get('enableReading'):
        #     rights.append(trading_backend.enums.APIKeyRights.READING)
        # if restrictions.get('enableSpotAndMarginTrading'):
        #     rights.append(trading_backend.enums.APIKeyRights.SPOT_TRADING)
        #     rights.append(trading_backend.enums.APIKeyRights.MARGIN_TRADING)
        # if restrictions.get('enableFutures'):
        #     rights.append(trading_backend.enums.APIKeyRights.FUTURES_TRADING)
        # if restrictions.get('permitsUniversalTransfer'):
        #     rights.append(trading_backend.enums.APIKeyRights.WITHDRAWALS)
        # return rights

    def get_orders_parameters(self, params=None) -> dict:
        if self._exchange.connector.client.options.get("broker", None) != self._get_id():
            self._exchange.connector.client.options["broker"] = self._get_id()
        return super().get_orders_parameters(params)
