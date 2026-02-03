import pytest
import ccxt

import trading_backend.errors


async def check_invalid_account(exchange):
    with pytest.raises(trading_backend.errors.ExchangeAuthError):
        # no API keys
        assert await exchange.is_valid_account()
    with pytest.raises(trading_backend.errors.ExchangeAuthError):
        # ValueError turned into ccxt.AuthenticationError
        exchange._exchange.connector.client.apiKey = "organizations/-4ab5-a606-578b4d74f3db"
        exchange._exchange.connector.client.secret = "-----BEGIN EC PRIVATE KEY"
        assert await exchange.is_valid_account()


async def check_invalid_account_keys_rights(exchange):
    with pytest.raises(ccxt.AuthenticationError):
        # no API keys
        assert await exchange._get_api_key_rights()
    with pytest.raises(ccxt.AuthenticationError):
        # ValueError turned into ccxt.AuthenticationError
        exchange._exchange.connector.client.apiKey = "organizations/-4ab5-a606-578b4d74f3db"
        exchange._exchange.connector.client.secret = "-----BEGIN EC PRIVATE KEY"
        assert await exchange._get_api_key_rights()
