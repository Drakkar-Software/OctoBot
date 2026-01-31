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
import ccxt.async_support
import trading_backend.exchanges as exchanges
import tests.util.create_order_tests as create_order_tests
from tests import coinbase_exchange


def test_get_name(coinbase_exchange):
    assert exchanges.Coinbase(coinbase_exchange).get_name() == ccxt.async_support.coinbase().id.lower()


@pytest.mark.asyncio
async def test_get_orders_parameters(coinbase_exchange):
    exchange = exchanges.Coinbase(coinbase_exchange)
    await create_order_tests.create_order_mocked_test_args(
        exchange,
        exchange_private_post_order_method_name="v3PrivatePostBrokerageOrders",
        exchange_request_referral_key="client_order_id",
        should_contains=True
    )


@pytest.mark.asyncio
async def test_inner_is_valid_account(coinbase_exchange):
    exchange = exchanges.Coinbase(coinbase_exchange)
    assert await exchange._inner_is_valid_account() == (False, await exchange._ensure_broker_status())


@pytest.mark.asyncio
async def test_invalid_api_key(coinbase_exchange):
    # _inner_is_valid_account is not implemented on coinbase
    pass


@pytest.mark.asyncio
async def test_invalid_api_key_get_api_key_rights(coinbase_exchange):
    # API keys used as a base for these tests are deleted from Coinbase
    exchange = exchanges.Coinbase(coinbase_exchange)
    with pytest.raises(ccxt.AuthenticationError):
        assert await exchange._get_api_key_rights()
    with pytest.raises(ccxt.AuthenticationError):
        # binascii.Error turned into ccxt.AuthenticationError
        exchange._exchange.connector.client.apiKey = "organizations/1e7665a0-440b-495f-8a49-5365841e196e/apiKeys/b43c5889-a3b5-4ab5-a606-578b4d74f3db"
        exchange._exchange.connector.client.secret = "AwEHoUQDQgAErQXGFQUMqPT5fQUVcCchCaomapu0y952"
        assert await exchange._get_api_key_rights()
    with pytest.raises(ccxt.AuthenticationError):
        # AssertionError turned into ccxt.AuthenticationError
        exchange._exchange.connector.client.apiKey = "organizations/1e7665a0-440b-495f-8a49-5365841e196e/apiKeys/b43c5889-a3b5-4ab5-a606-578b4d74f3db"
        exchange._exchange.connector.client.secret = "dd"
        assert await exchange._get_api_key_rights()
    with pytest.raises(ccxt.AuthenticationError):
        # IndexError turned into ccxt.AuthenticationError
        exchange._exchange.connector.client.apiKey = "organizations/1e7665a0-440b-495f-8a49-5365841e196e/apiKeys/b43c5889-a3b5-4ab5-a606-578b4d74f3db"
        exchange._exchange.connector.client.secret = "-----BEGIN EC PRIVATE KEY-----\nMHcCAQEEINpzmww4rUF+EeSMDnBqd3oXTxm2Q76MUwwsLw8Vjo+poAoGCCqGSM49\nBk6cNPNp4fH0NwneES1HNpJ0aEx+VYRhcg=="
        assert await exchange._get_api_key_rights()
    with pytest.raises(ccxt.AuthenticationError):
        # binascii.Error turned into ccxt.AuthenticationError
        exchange._exchange.connector.client.apiKey = "-495f-8a49-5365841e196e/apiKeys/b43c5889-a3b5-4ab5-a606-578b4d74f3db"
        exchange._exchange.connector.client.secret = "-----BEGIN EC PRIVATE KEY-----\nMHcCAQEEIK/XmQtNSTD2pqrhyZFvBuExnlyLOPcDzT+fsm1sq3ZCoAoGCCqGSM49\nAwEHoUQDQgAErQXGFQUMqPT5fQUVcCchCaomapu0y952+XgveL2QjgghGCeFbLfR\nTSg2RgUUtGbG3TIBEomwzbRAOEeYdjK06w"
        assert await exchange._get_api_key_rights()
    with pytest.raises(ccxt.AuthenticationError):
        # binascii.Error turned into ccxt.AuthenticationError
        exchange._exchange.connector.client.apiKey = "b43c5889-a3b5-4ab5-a606-578b4d74f3db"
        exchange._exchange.connector.client.secret = "-----BEGIN EC PRIVATE KEY-----\nMHcCAQEEIK/XmQtNSTD2pqrhyZFvBuExnlyLOPcDzT+fsm1sq3ZCoAoGCCqGSM49\nAwEHoUQDQgAErQXGFQUMqPT5fQUVcCchCaomapu0y952+XgveL2QjgghGCeFbLfR\nTSg2RgUUtGbG3TIBEomwzbRAOEeYdjK06w"
        assert await exchange._get_api_key_rights()
    with pytest.raises(ccxt.AuthenticationError):
        # swapped private and public
        # ccxt.ArgumentsRequired turned into ccxt.AuthenticationError
        exchange._exchange.connector.client.apiKey = "-----BEGIN EC PRIVATE KEY----b43c5889-a3b5-4ab5-a606-578b4d74f3db"
        exchange._exchange.connector.client.secret = "-----BEGIN EC PRIVATE KEY-----\nMHcCAQEEIK/XmQtNSTD2pqrhyZFvBuExnlyLOPcDzT+fsm1sq3ZCoAoGCCqGSM49\nAwEHoUQDQgAErQXGFQUMqPT5fQUVcCchCaomapu0y952+XgveL2QjgghGCeFbLfR\nTSg2RgUUtGbG3TIBEomwzbRAOEeYdjK06w"
        assert await exchange._get_api_key_rights()
    with pytest.raises(ccxt.AuthenticationError):
        # added chars after private key
        # ccxt.static_dependencies.ecdsa.der.UnexpectedDER turned into ccxt.AuthenticationError
        exchange._exchange.connector.client.apiKey = "organizations/1e7665a0-440b-495f-8a49-5365841e196e/apiKeys/b43c5889-a3b5-4ab5-a606-578b4d74f3db"
        exchange._exchange.connector.client.secret = "-----BEGIN EC PRIVATE KEY-----\nMHcCAQEEIK/XmQtNSTD2pqrhyZFvBuExnlyLOPcDzT+fsm1sq3ZCoAoGCCqGSM49\nAwEHoUQDQgAErQXGFQUMqPT5fQUVcCchCaomapu0y952+XgveL2QjgghGCeFbLfR\nTSg2RgUUtGbG3TIBEomwzbRAOEeYdjK06w" + b'488347'.decode()
        assert await exchange._get_api_key_rights()


# @pytest.mark.asyncio
# async def test_get_api_key_rights(coinbase_exchange):
#     exchange = exchanges.Coinbase(coinbase_exchange)
#     with mock.patch.object(
#         exchange._exchange.connector.client, "v2PrivateGetUserAuth",
#         mock.AsyncMock(return_value={"data": {"scopes": [
#             "rat#view",
#             "rat#trade",
#             "rat#transfer",
#         ]}})
#     ) as v2PrivateGetUserAuth_mock:
#         assert await exchange._get_api_key_rights() == [
#             trading_backend.enums.APIKeyRights.READING,
#             trading_backend.enums.APIKeyRights.SPOT_TRADING,
#             trading_backend.enums.APIKeyRights.MARGIN_TRADING,
#             trading_backend.enums.APIKeyRights.FUTURES_TRADING,
#             trading_backend.enums.APIKeyRights.WITHDRAWALS,
#         ]
#         v2PrivateGetUserAuth_mock.assert_awaited_once()
#     with mock.patch.object(
#         exchange._exchange.connector.client, "v2PrivateGetUserAuth",
#         mock.AsyncMock(return_value={"data": {"scopes": [
#             "rat#view",
#             "rat#trade",
#         ]}})
#     ) as v2PrivateGetUserAuth_mock:
#         assert await exchange._get_api_key_rights() == [
#             trading_backend.enums.APIKeyRights.READING,
#             trading_backend.enums.APIKeyRights.SPOT_TRADING,
#             trading_backend.enums.APIKeyRights.MARGIN_TRADING,
#             trading_backend.enums.APIKeyRights.FUTURES_TRADING,
#         ]
#         v2PrivateGetUserAuth_mock.assert_awaited_once()
#     with mock.patch.object(
#         exchange._exchange.connector.client, "v2PrivateGetUserAuth",
#         mock.AsyncMock(return_value={"data": {"scopes": [
#             "wallet:accounts:read",
#             "wallet:buys:read",
#             "wallet:sells:read",
#             "wallet:orders:read",
#             "wallet:trades:read",
#             "wallet:user:read",
#             "wallet:transactions:read",
#             "wallet:buys:create",
#         ]}})
#     ) as v2PrivateGetUserAuth_mock:
#         assert await exchange._get_api_key_rights() == [
#             trading_backend.enums.APIKeyRights.READING
#         ]
#         v2PrivateGetUserAuth_mock.assert_awaited_once()
#     with mock.patch.object(
#         exchange._exchange.connector.client, "v2PrivateGetUserAuth",
#         mock.AsyncMock(return_value={"data": {"scopes": [
#             "wallet:accounts:read",
#             "wallet:buys:read",
#             "wallet:sells:read",
#             "wallet:orders:read",
#             "wallet:trades:read",
#             "wallet:user:read",
#             "wallet:transactions:read",
#             "wallet:buys:create",
#             "wallet:sells:create",
#             "wallet:withdrawals:create",
#         ]}})
#     ) as v2PrivateGetUserAuth_mock:
#         assert await exchange._get_api_key_rights() == [
#             trading_backend.enums.APIKeyRights.READING,
#             trading_backend.enums.APIKeyRights.SPOT_TRADING,
#             trading_backend.enums.APIKeyRights.MARGIN_TRADING,
#             trading_backend.enums.APIKeyRights.FUTURES_TRADING,
#             trading_backend.enums.APIKeyRights.WITHDRAWALS
#         ]
#         v2PrivateGetUserAuth_mock.assert_awaited_once()
