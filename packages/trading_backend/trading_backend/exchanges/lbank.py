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


class LBank(exchanges.Exchange):
    IS_SPONSORING = False

    @classmethod
    def get_name(cls):
        return 'lbank'

    async def _get_api_key_rights(self) -> list[trading_backend.enums.APIKeyRights]:
        restrictions = await self._exchange.connector.client.spotPrivatePostSupplementApiRestrictions()
        data = self._exchange.connector.client.safe_value(restrictions, 'data', {})
        rights = []
        if data.get('enableReading', False):
            rights.append(trading_backend.enums.APIKeyRights.READING)
        if data.get('enableSpotTrading', False):
            rights.append(trading_backend.enums.APIKeyRights.SPOT_TRADING)
            rights.append(trading_backend.enums.APIKeyRights.MARGIN_TRADING)
        if data.get('enableFuturesTrading', False):
            rights.append(trading_backend.enums.APIKeyRights.FUTURES_TRADING)
        if data.get('enableWithdrawals', False):
            rights.append(trading_backend.enums.APIKeyRights.WITHDRAWALS)
        return rights
