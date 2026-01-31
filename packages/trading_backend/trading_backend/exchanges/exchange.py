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
import contextlib
import aiohttp
try:
    from aiohttp_socks import ProxyConnectionError
except ImportError:
    # local mock in case aiohttp_socks is not available
    class ProxyConnectionError(Exception):
        pass

import trading_backend.errors
import trading_backend.enums
import trading_backend.constants


class Exchange:
    SPOT_ID = None
    MARGIN_ID = None
    FUTURE_ID = None
    IS_SPONSORING = False
    ORDER_ID = "12345"

    def __init__(self, exchange):
        self._exchange = exchange

        # add backend headers
        self._exchange.connector.add_headers(self.get_headers())

    def stop(self):
        self._exchange = None

    @classmethod
    def get_name(cls):
        return 'default'

    @classmethod
    def is_sponsoring(cls) -> bool:
        return cls.IS_SPONSORING

    async def initialize(self) -> str:
        default = f"{self.get_name().capitalize()} backend initialized."
        return f"{default} {await self._ensure_broker_status()}" if self.is_sponsoring() else default

    async def _ensure_broker_status(self):
        return f"Broker rebate is enabled."

    def get_headers(self) -> dict:
        return {}

    def get_orders_parameters(self, params=None) -> dict:
        if params is None:
            params = {}
        return params

    def _allow_withdrawal_right(self) -> bool:
        return trading_backend.constants.ALLOW_WITHDRAWAL_KEYS

    def _get_symbol(self):
        if self._exchange.exchange_manager.is_future:
            return "BTC/USDT:USDT"
        return "BTC/USDT"

    async def _inner_cancel_order(self):    
        await self._exchange.connector.client.cancel_order(self.ORDER_ID, symbol=self._get_symbol())


    async def _get_api_key_rights_using_order(self) -> list[trading_backend.enums.APIKeyRights]:
        rights = [trading_backend.enums.APIKeyRights.READING]
        try:
            with self.error_describer():
                await self._inner_cancel_order()
        except ccxt.AuthenticationError as err:
            if self._exchange.is_api_permission_error(err):
                # does not have trading permission: do not add trading permissions to rights
                pass
            else:
                self.raise_accurate_auth_error_if_any(err)
                raise
        except ccxt.InvalidNonce as err:
            raise trading_backend.errors.TimeSyncError(err) from err
        except (ccxt.BadSymbol, ccxt.OperationFailed) as err:  
            # should not happen
            raise trading_backend.errors.UnexpectedError(err) from err
        except ccxt.ExchangeError as err:
            self.raise_accurate_auth_error_if_any(err)
            if not self._exchange.is_api_permission_error(err):
                # goal of the check: we are in the expected "order not found" error scenario
                # => has trading permission
                rights.append(trading_backend.enums.APIKeyRights.SPOT_TRADING)
                rights.append(trading_backend.enums.APIKeyRights.MARGIN_TRADING)
                rights.append(trading_backend.enums.APIKeyRights.FUTURES_TRADING)
        return rights

    def raise_accurate_auth_error_if_any(self, err):
        if self._exchange.is_ip_whitelist_error(err):
            raise trading_backend.errors.APIKeyIPWhitelistError(err) from err
        if self._exchange.is_authentication_error(err):
            raise ccxt.AuthenticationError(err) from err

    async def _get_api_key_rights(self) -> list[trading_backend.enums.APIKeyRights]:
        # default implementation: fetch portfolio and don't check
        # todo implementation for each exchange as long as ccxt does not support it in unified api
        with self.error_describer():
            await self._exchange.connector.client.fetch_balance()
        return [
            trading_backend.enums.APIKeyRights.READING,
            trading_backend.enums.APIKeyRights.SPOT_TRADING,
            trading_backend.enums.APIKeyRights.FUTURES_TRADING,
            trading_backend.enums.APIKeyRights.MARGIN_TRADING,
        ]

    async def _ensure_api_key_rights(self):
        # raise trading_backend.errors.APIKeyPermissionsError on missing permissions
        rights = []
        try:
            rights = await self._get_api_key_rights()
        except ccxt.BaseError as err:
            try:
                import octobot_commons.logging as logging
                logging.get_logger(self.__class__.__name__).info(
                    f"Error when checking {self.__class__.__name__} api key rights: {err} ({err.__class__.__name__})"
                )
            except ImportError:
                pass
            raise err
        except (trading_backend.errors.ExchangeAuthError, trading_backend.errors.UnexpectedError):
            # forward error
            raise
        except Exception as err:
            try:
                import octobot_commons.logging as logging
                logging.get_logger(self.__class__.__name__).exception(
                    err, True, f"Error when getting {self.__class__.__name__} api key rights: {err}"
                )
            except ImportError:
                pass
            # non ccxt error: proceed to right checks and raise
        required_right = trading_backend.enums.APIKeyRights.SPOT_TRADING
        if self._exchange.exchange_manager.is_future:
            required_right = trading_backend.enums.APIKeyRights.FUTURES_TRADING
        if self._exchange.exchange_manager.is_margin:
            required_right = trading_backend.enums.APIKeyRights.MARGIN_TRADING
        if required_right not in rights:
            raise trading_backend.errors.APIKeyPermissionsError(
                f"{required_right.value} permission is required"
            )
        if not self._allow_withdrawal_right() and trading_backend.enums.APIKeyRights.WITHDRAWALS in rights:
            raise trading_backend.errors.APIKeyPermissionsError(
                f"This api key has withdrawal rights, please revoke it."
            )

    async def is_valid_account(self, always_check_key_rights=False) -> (bool, str):
        try:
            # 1. check account
            validity, message = await self._inner_is_valid_account()
            if not always_check_key_rights and not validity:
                return validity, message
            # 2. check api key right
            await self._ensure_api_key_rights()
            return validity, message
        except trading_backend.errors.ExchangeAuthError:
            # forward exception
            raise
        except ccxt.InvalidNonce as err:
            raise trading_backend.errors.TimeSyncError(err)
        except ccxt.NetworkError as err:
            raise trading_backend.errors.NetworkError(err)
        except ccxt.ExchangeError as err:
            raise trading_backend.errors.ExchangeAuthError(err)
        except trading_backend.errors.InvalidIdError as err:
            try:
                import octobot_commons.logging as logging
                logging.get_logger(self.__class__.__name__).error(
                    f"{trading_backend.errors.InvalidIdError.__name__} when checking account validity: {err}"
                )
            except ImportError:
                pass
            raise trading_backend.errors.ExchangeAuthError(err)

    async def _inner_is_valid_account(self) -> (bool, str):
        # check account validity regarding exchange requirements, exchange specific
        return True, None

    def _get_id(self):
        if self._exchange.exchange_manager.is_future:
            return self.FUTURE_ID
        if self._exchange.exchange_manager.is_margin:
            return self.MARGIN_ID
        return self.SPOT_ID

    @contextlib.contextmanager
    def error_describer(self):
        """
        Note: does not change the exception class unless it's a proxy connection issue
        """
        try:
            yield
        except (
            # Generic connection / exchange error
            ccxt.ExchangeNotAvailable, ccxt.AuthenticationError, ccxt.ExchangeError,
            # Proxy errors
            aiohttp.ClientHttpProxyError, aiohttp.ClientProxyConnectionError, ProxyConnectionError
        ) as err:
            try:
                self._exchange.connector.raise_or_prefix_proxy_error_if_relevant(err, None)
            except ccxt.BaseError:
                raise
            except Exception as err:
                # wrap error into local trading_backend.errors.UnexpectedError
                raise trading_backend.errors.UnexpectedError(err) from err
