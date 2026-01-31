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
import ccxt.static_dependencies.ecdsa.der
import binascii
import trading_backend.exchanges as exchanges
import trading_backend.enums


class Coinbase(exchanges.Exchange):
    # todo update this when coinbase broker id is available
    SPOT_ID = "octobot"
    MARGIN_ID = "octobot"
    FUTURE_ID = "octobot"
    REF_ID = None
    IS_SPONSORING = True
    ORDER_ID = "8bb80a81-27f7-4415-aa50-911ea46d841c"

    @classmethod
    def get_name(cls):
        return 'coinbase'

    def get_orders_parameters(self, params=None) -> dict:
        if self._exchange.connector.client.options.get("brokerId", None) != self._get_id():
            self._exchange.connector.client.options["brokerId"] = self._get_id()
        return super().get_orders_parameters(params)

    def _get_legacy_api_permissions(self, scopes):
        rights = []
        read_scopes = [
            "wallet:accounts:read",
            "wallet:buys:read",
            "wallet:sells:read",
            "wallet:orders:read",
            "wallet:trades:read",
            "wallet:user:read",
            "wallet:transactions:read",
        ]
        trade_scopes = [
            "wallet:buys:create",
            "wallet:sells:create",
        ]
        withdraw_scopes = [
            "wallet:withdrawals:create"
        ]
        if all(scope in scopes for scope in read_scopes):
            rights.append(trading_backend.enums.APIKeyRights.READING)
        if all(scope in scopes for scope in trade_scopes):
            rights.append(trading_backend.enums.APIKeyRights.SPOT_TRADING)
            rights.append(trading_backend.enums.APIKeyRights.MARGIN_TRADING)
            rights.append(trading_backend.enums.APIKeyRights.FUTURES_TRADING)
        if any(scope in scopes for scope in withdraw_scopes):
            rights.append(trading_backend.enums.APIKeyRights.WITHDRAWALS)
        return rights

    def _get_api_permissions(self, scopes):
        rights = []
        read_scopes = [
            "rat#view",
        ]
        trade_scopes = [
            "rat#trade",
        ]
        withdraw_scopes = [
            "rat#transfer"
        ]
        if all(scope in scopes for scope in read_scopes):
            rights.append(trading_backend.enums.APIKeyRights.READING)
        if all(scope in scopes for scope in trade_scopes):
            rights.append(trading_backend.enums.APIKeyRights.SPOT_TRADING)
            rights.append(trading_backend.enums.APIKeyRights.MARGIN_TRADING)
            rights.append(trading_backend.enums.APIKeyRights.FUTURES_TRADING)
        if any(scope in scopes for scope in withdraw_scopes):
            rights.append(trading_backend.enums.APIKeyRights.WITHDRAWALS)
        return rights

    async def _inner_cancel_order(self):
        try:
            await super()._inner_cancel_order()
            # also try to fetch balance on coinbase
            await self._exchange.connector.client.fetch_balance(params={"v3":True})
        except ccxt.ArgumentsRequired as err:
            # raised on invalid api keys
            raise ccxt.AuthenticationError(err) from err

    async def _get_api_key_rights(self) -> list[trading_backend.enums.APIKeyRights]:
        # warning might become deprecated
        # https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/api-users
        try:
            return await self._get_api_key_rights_using_order()
        except ccxt.AuthenticationError:
            raise
        except (
            binascii.Error, AssertionError, IndexError,
            ccxt.ArgumentsRequired, ccxt.static_dependencies.ecdsa.der.UnexpectedDER
        ) as err:
            raise ccxt.AuthenticationError(f"Invalid key format ({err})")

    async def _inner_is_valid_account(self) -> (bool, str):
        return False, await self._ensure_broker_status()
