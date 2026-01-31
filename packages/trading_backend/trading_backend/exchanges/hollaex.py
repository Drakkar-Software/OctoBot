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

import trading_backend.enums
import trading_backend.exchanges as exchanges


class HollaEx(exchanges.Exchange):
    # todo later: add local HollaEx-powered exchange ID when necessary
    SPOT_ID = None
    MARGIN_ID = None
    FUTURE_ID = None
    IS_SPONSORING = False

    @classmethod
    def get_name(cls):
        return 'hollaex'

    async def _get_api_key_rights(self) -> list[trading_backend.enums.APIKeyRights]:
        # It is currently impossible to fetch api key permissions: try to cancel an imaginary order,
        # if a permission error is raised instead of a cancel fail, then trading permissions are missing.
        # updated: 18/09/2024
        return await self._get_api_key_rights_using_order()
