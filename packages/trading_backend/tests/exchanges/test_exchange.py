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
import pytest
import mock
import ccxt

import trading_backend.exchanges as exchanges
import trading_backend.errors
import trading_backend.enums
from trading_backend.exchanges.exchange import ProxyConnectionError
from tests import default_exchange


def test_get_name(default_exchange):
    assert exchanges.Exchange(default_exchange).get_name() == exchanges.Exchange.get_name()


def test_get_orders_parameters(default_exchange):
    assert exchanges.Exchange(default_exchange).get_orders_parameters({"a": 1}) == {"a": 1}


@pytest.mark.asyncio
async def test_is_valid_account(default_exchange):
    exchange = exchanges.Exchange(default_exchange)
    with mock.patch.object(exchange._exchange.connector.client, "fetch_balance",
                           mock.AsyncMock(return_value=None)) as fetch_balance_mock:
        assert await exchange.is_valid_account() == (True, None)
        fetch_balance_mock.assert_called_once()
    with mock.patch.object(exchange._exchange.connector.client, "fetch_balance",
                           mock.AsyncMock(side_effect=ccxt.AuthenticationError)) as fetch_balance_mock:
        with pytest.raises(trading_backend.errors.ExchangeAuthError):
            assert await exchange.is_valid_account() == (True, None)
        fetch_balance_mock.assert_called_once()
    with mock.patch.object(exchange._exchange.connector.client, "fetch_balance",
                           mock.AsyncMock(side_effect=KeyError)) as fetch_balance_mock:
        # non ccxt error: proceed to right checks and raise
        with pytest.raises(trading_backend.errors.APIKeyPermissionsError):
            assert await exchange.is_valid_account() == (True, None)
        fetch_balance_mock.assert_called_once()
    with mock.patch.object(exchange._exchange.connector.client, "fetch_balance",
                           mock.AsyncMock(side_effect=ProxyConnectionError)) as fetch_balance_mock:
        # non ccxt error: proceed to right checks and raise
        with pytest.raises(trading_backend.errors.UnexpectedError):
            assert await exchange.is_valid_account() == (True, None)
        fetch_balance_mock.assert_called_once()
    with mock.patch.object(exchange._exchange.connector.client, "fetch_balance",
                           mock.AsyncMock(side_effect=ccxt.InvalidNonce)) as fetch_balance_mock:
        with pytest.raises(trading_backend.errors.TimeSyncError):
            assert await exchange.is_valid_account() == (True, None)
        fetch_balance_mock.assert_called_once()
    with (mock.patch.object(exchange, "_inner_is_valid_account",
                           mock.AsyncMock(side_effect=trading_backend.errors.InvalidIdError))
          as _inner_is_valid_account_mock):
        with pytest.raises(trading_backend.errors.ExchangeAuthError):
            assert await exchange.is_valid_account() == (True, None)
        _inner_is_valid_account_mock.assert_called_once()


@pytest.mark.asyncio
async def test_get_api_key_rights_using_order(default_exchange):
    exchange = exchanges.Exchange(default_exchange)
    read_only_rights = [
        trading_backend.enums.APIKeyRights.READING,
    ]
    trading_rights = read_only_rights + [
        trading_backend.enums.APIKeyRights.SPOT_TRADING,
        trading_backend.enums.APIKeyRights.MARGIN_TRADING,
        trading_backend.enums.APIKeyRights.FUTURES_TRADING,
    ]
    # normal cases
    with mock.patch.object(
        exchange._exchange.connector.client, "cancel_order", mock.AsyncMock()
    ) as cancel_order_mock:
        assert await exchange._get_api_key_rights_using_order() == read_only_rights
        cancel_order_mock.assert_called_once()
    with mock.patch.object(
        exchange._exchange.connector.client, "cancel_order", mock.AsyncMock(side_effect=ccxt.OrderNotFound)
    ) as cancel_order_mock:
        assert await exchange._get_api_key_rights_using_order() == trading_rights
        cancel_order_mock.assert_called_once()

    # error case 1: is_api_permission_error = True
    with mock.patch.object(
        exchange._exchange, "is_api_permission_error", mock.Mock(return_value=True)
    ) as is_api_permission_error_mock:
        with mock.patch.object(
            exchange._exchange.connector.client, "cancel_order", mock.AsyncMock(side_effect=ccxt.AuthenticationError)
        ) as cancel_order_mock:
            assert await exchange._get_api_key_rights_using_order() == read_only_rights
            cancel_order_mock.assert_called_once()
            is_api_permission_error_mock.assert_called_once()
            is_api_permission_error_mock.reset_mock()
        with mock.patch.object(
            # random ccxt error
            exchange._exchange.connector.client, "cancel_order", mock.AsyncMock(side_effect=ccxt.BadRequest)
        ) as cancel_order_mock:
            assert await exchange._get_api_key_rights_using_order() == read_only_rights
            cancel_order_mock.assert_called_once()
            is_api_permission_error_mock.assert_called_once()
            is_api_permission_error_mock.reset_mock()
        with mock.patch.object(
            exchange._exchange.connector.client, "cancel_order", mock.AsyncMock(side_effect=ccxt.BadSymbol)
        ) as cancel_order_mock:
            # unexpected error
            with pytest.raises(trading_backend.errors.UnexpectedError):
                await exchange._get_api_key_rights_using_order()
                cancel_order_mock.assert_not_called()
                is_api_permission_error_mock.assert_not_called()

        # error case 1: is_api_permission_error = False
        with mock.patch.object(
            exchange._exchange, "is_api_permission_error", mock.Mock(return_value=False)
        ) as is_api_permission_error_mock:
            # A. no accurate error
            with mock.patch.object(
                exchange, "raise_accurate_auth_error_if_any", mock.Mock()
            ) as raise_accurate_auth_error_if_any_mock:
                with mock.patch.object(
                    exchange._exchange.connector.client, "cancel_order",
                    mock.AsyncMock(side_effect=ccxt.AuthenticationError)
                ) as cancel_order_mock:
                    with pytest.raises(ccxt.AuthenticationError):
                        await exchange._get_api_key_rights_using_order()
                    raise_accurate_auth_error_if_any_mock.assert_called_once()
                    raise_accurate_auth_error_if_any_mock.reset_mock()
                    cancel_order_mock.assert_called_once()
                    is_api_permission_error_mock.assert_called_once()
                    is_api_permission_error_mock.reset_mock()
                with mock.patch.object(
                    exchange._exchange.connector.client, "cancel_order",
                    mock.AsyncMock(side_effect=ccxt.RequestTimeout)
                ) as cancel_order_mock:
                    with pytest.raises(trading_backend.errors.UnexpectedError):
                        await exchange._get_api_key_rights_using_order()
                    cancel_order_mock.assert_called_once()
                    raise_accurate_auth_error_if_any_mock.assert_not_called()
                    is_api_permission_error_mock.assert_not_called()
                with mock.patch.object(
                    exchange._exchange.connector.client, "cancel_order",
                    mock.AsyncMock(side_effect=ccxt.InsufficientFunds)
                ) as cancel_order_mock:
                    assert await exchange._get_api_key_rights_using_order() == trading_rights
                    raise_accurate_auth_error_if_any_mock.assert_called_once()
                    raise_accurate_auth_error_if_any_mock.reset_mock()
                    is_api_permission_error_mock.assert_called_once()
                    is_api_permission_error_mock.reset_mock()
                    cancel_order_mock.assert_called_once()

            # B. accurate error
            with mock.patch.object(
                exchange, "raise_accurate_auth_error_if_any", mock.Mock(
                    side_effect=trading_backend.errors.APIKeyIPWhitelistError
                    )
            ) as raise_accurate_auth_error_if_any_mock:
                with mock.patch.object(
                    exchange._exchange.connector.client, "cancel_order",
                    mock.AsyncMock(side_effect=ccxt.AuthenticationError)
                ) as cancel_order_mock:
                    with pytest.raises(trading_backend.errors.APIKeyIPWhitelistError):
                        await exchange._get_api_key_rights_using_order()
                    raise_accurate_auth_error_if_any_mock.assert_called_once()
                    raise_accurate_auth_error_if_any_mock.reset_mock()
                    cancel_order_mock.assert_called_once()
                    is_api_permission_error_mock.assert_called_once()
                    is_api_permission_error_mock.reset_mock()
                with mock.patch.object(
                    exchange._exchange.connector.client, "cancel_order",
                    mock.AsyncMock(side_effect=ccxt.RequestTimeout)
                ) as cancel_order_mock:
                    with pytest.raises(trading_backend.errors.UnexpectedError):
                        await exchange._get_api_key_rights_using_order()
                    cancel_order_mock.assert_called_once()
                    raise_accurate_auth_error_if_any_mock.assert_not_called()
                    is_api_permission_error_mock.assert_not_called()
                with mock.patch.object(
                    exchange._exchange.connector.client, "cancel_order",
                    mock.AsyncMock(side_effect=ccxt.InsufficientFunds)
                ) as cancel_order_mock:
                    with pytest.raises(trading_backend.errors.APIKeyIPWhitelistError):
                        await exchange._get_api_key_rights_using_order()
                    raise_accurate_auth_error_if_any_mock.assert_called_once()
                    raise_accurate_auth_error_if_any_mock.reset_mock()
                    is_api_permission_error_mock.assert_not_called()
                    cancel_order_mock.assert_called_once()


def test_raise_accurate_auth_error_if_any(default_exchange):
    exchange = exchanges.Exchange(default_exchange)

    with mock.patch.object(
        exchange._exchange, "is_authentication_error", mock.Mock(return_value=False)
    ), mock.patch.object(
        exchange._exchange, "is_ip_whitelist_error", mock.Mock(return_value=False)
    ):
        assert exchange.raise_accurate_auth_error_if_any(NotImplementedError("plop")) is None

    with mock.patch.object(
        exchange._exchange, "is_authentication_error", mock.Mock(return_value=True)
    ), mock.patch.object(
        exchange._exchange, "is_ip_whitelist_error", mock.Mock(return_value=False)
    ):
        with pytest.raises(ccxt.AuthenticationError, match="plop"):
            exchange.raise_accurate_auth_error_if_any(NotImplementedError("plop"))

    with mock.patch.object(
        exchange._exchange, "is_authentication_error", mock.Mock(return_value=False)
    ), mock.patch.object(
        exchange._exchange, "is_ip_whitelist_error", mock.Mock(return_value=True)
    ):
        with pytest.raises(trading_backend.APIKeyIPWhitelistError, match="plop"):
            exchange.raise_accurate_auth_error_if_any(NotImplementedError("plop"))

    with mock.patch.object(
        exchange._exchange, "is_authentication_error", mock.Mock(return_value=True)
    ), mock.patch.object(
        exchange._exchange, "is_ip_whitelist_error", mock.Mock(return_value=True)
    ):
        with pytest.raises(trading_backend.APIKeyIPWhitelistError, match="plop"):
            exchange.raise_accurate_auth_error_if_any(NotImplementedError("plop"))


@pytest.mark.asyncio
async def test_initialize(default_exchange):
    exchange = exchanges.Exchange(default_exchange)
    init_result = await exchange.initialize()
    assert exchange.get_name().capitalize() in init_result
    assert "Broker" not in init_result


@pytest.mark.asyncio
async def test_ensure_broker_status(default_exchange):
    init_result = await exchanges.Exchange(default_exchange)._ensure_broker_status()
    assert "Broker" in init_result
    assert "enabled" in init_result
