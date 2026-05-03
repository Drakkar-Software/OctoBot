#  Drakkar-Software OctoBot-Tentacles
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
import typing
import ccxt.async_support

import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants


class BitMartConnector(exchanges.CCXTConnector):

    def _client_factory(
        self,
        force_unauth,
        keys_adapter: typing.Callable[[exchanges.ExchangeCredentialsData], exchanges.ExchangeCredentialsData]=None
    ) -> tuple:
        client, is_authenticated = super()._client_factory(force_unauth, keys_adapter=self._keys_adapter)
        return client, is_authenticated

    def _keys_adapter(self, creds: exchanges.ExchangeCredentialsData) -> exchanges.ExchangeCredentialsData:
        # use password as uid
        creds.uid = creds.password
        creds.password = None
        return creds


class BitMart(exchanges.RestExchange):
    DEFAULT_CONNECTOR_CLASS = BitMartConnector

    @classmethod
    def get_name(cls):
        return 'bitmart'
