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


class BinanceUS(exchanges.Exchange):
    # todo update this when binanceus broker id is available
    SPOT_ID = None
    MARGIN_ID = None
    FUTURE_ID = None
    REF_ID = None
    IS_SPONSORING = False

    @classmethod
    def get_name(cls):
        return 'binanceus'

    async def _ensure_broker_status(self):
        return f"Broker rebate is not enabled (missing broker id)."

    async def _get_api_key_rights(self) -> list[trading_backend.enums.APIKeyRights]:
        # Binance.us specific:
        # It is currently impossible to fetch api key permissions: try to cancel an imaginary order,
        # if a permission error is raised instead of a cancel fail, then trading permissions are missing.
        # updated: 14/04/2024
        try:
            return await self._get_api_key_rights_using_order()
        except ValueError as err:
            raise ccxt.AuthenticationError(f"Invalid key format ({err})")
        # raising 404 error
        # restrictions = await self._exchange.connector.client.sapi_get_account_apirestrictions()
        # rights = []
        # if restrictions.get('enableReading'):
        #     rights.append(trading_backend.enums.APIKeyRights.READING)
        # if restrictions.get('enableSpotAndMarginTrading'):
        #     rights.append(trading_backend.enums.APIKeyRights.SPOT_TRADING)
        #     rights.append(trading_backend.enums.APIKeyRights.MARGIN_TRADING)
        #     rights.append(trading_backend.enums.APIKeyRights.FUTURES_TRADING)
        # if restrictions.get('enableWithdrawals'):
        #     rights.append(trading_backend.enums.APIKeyRights.WITHDRAWALS)
        # return rights

    async def _inner_is_valid_account(self) -> (bool, str):
        return False, await self._ensure_broker_status()
