#  Drakkar-Software OctoBot-Trading
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
import contextlib
import pytest
import mock
import aiohttp
import ccxt.async_support as ccxt

import octobot_commons.aiohttp_util as aiohttp_util

import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.connectors.ccxt.ccxt_client_util as ccxt_client_util
import octobot_trading.constants as constants


@pytest.mark.asyncio
async def test_proxies():
    with mock.patch.object(aiohttp.ClientSession, "_request", mock.AsyncMock()) as _request_mock:

        # no proxy
        proxy_config = exchanges.ExchangeProxyConfig()
        async with _exchange_with_proxy_config(proxy_config) as exchange:
            _request_mock.assert_not_called()
            await exchange.load_markets()
            assert _request_mock.call_count > 0
            assert all(
                call.kwargs["proxy"] is None
                for call in _request_mock.call_args_list
            )
            _request_mock.reset_mock()

        # http proxy
        proxy_config = exchanges.ExchangeProxyConfig(
            http_proxy="http://127.0.0.1:9090",
        )
        async with _exchange_with_proxy_config(proxy_config) as exchange:
            _request_mock.assert_not_called()
            await exchange.load_markets()
            assert _request_mock.call_count > 0
            assert all(
                call.kwargs["proxy"] == "http://127.0.0.1:9090"
                for call in _request_mock.call_args_list
            )
            _request_mock.reset_mock()

        # http proxy callback
        proxy_config = exchanges.ExchangeProxyConfig(
            http_proxy_callback=lambda url, method, headers, body: "http://9.9.9.9:9090",
        )
        async with _exchange_with_proxy_config(proxy_config) as exchange:
            _request_mock.assert_not_called()
            await exchange.load_markets()
            assert _request_mock.call_count > 0
            assert all(
                call.kwargs["proxy"] == "http://9.9.9.9:9090"
                for call in _request_mock.call_args_list
            )
            _request_mock.reset_mock()

        # https proxy
        proxy_config = exchanges.ExchangeProxyConfig(
            https_proxy="https://127.0.0.1:9090",
        )
        async with _exchange_with_proxy_config(proxy_config) as exchange:
            _request_mock.assert_not_called()
            await exchange.load_markets()
            assert _request_mock.call_count > 0
            assert all(
                call.kwargs["proxy"] == "https://127.0.0.1:9090"
                for call in _request_mock.call_args_list
            )
            _request_mock.reset_mock()

        # https proxy callback
        proxy_config = exchanges.ExchangeProxyConfig(
            https_proxy_callback=lambda url, method, headers, body: "https://9.9.9.9:9090",
        )
        async with _exchange_with_proxy_config(proxy_config) as exchange:
            _request_mock.assert_not_called()
            await exchange.load_markets()
            assert _request_mock.call_count > 0
            assert all(
                call.kwargs["proxy"] == "https://9.9.9.9:9090"
                for call in _request_mock.call_args_list
            )
            _request_mock.reset_mock()

        # https proxy callback
        proxy_config = exchanges.ExchangeProxyConfig(
            https_proxy_callback=lambda url, method, headers, body: "https://9.9.9.9:9090",
        )
        async with _exchange_with_proxy_config(proxy_config) as exchange:
            _request_mock.assert_not_called()
            await exchange.load_markets()
            assert _request_mock.call_count > 0
            assert all(
                call.kwargs["proxy"] == "https://9.9.9.9:9090"
                for call in _request_mock.call_args_list
            )
            _request_mock.reset_mock()


@pytest.mark.asyncio
async def test_request_counter():
    with mock.patch.object(aiohttp.ClientSession, "_request", mock.AsyncMock()) as _request_mock:
        # without proxy
        proxy_config = exchanges.ExchangeProxyConfig()
        with mock.patch.object(constants, "ENABLE_CCXT_REQUESTS_COUNTER", True):
            async with _exchange_with_proxy_config(proxy_config, allow_request_counter=True) as exchange:
                await exchange.load_markets()
                assert _request_mock.call_count > 0
                assert all(
                    call.kwargs["proxy"] is None
                    for call in _request_mock.call_args_list
                )
                assert isinstance(exchange.session, aiohttp_util.CounterClientSession)
                # requests are counted by session counter
                assert len(exchange.session.per_min.paths) > 0
                assert exchange.session.per_min.paths[next(iter(exchange.session.per_min.paths))] > 0
        _request_mock.reset_mock()

        # with http proxy
        proxy_config = exchanges.ExchangeProxyConfig(http_proxy="http://127.0.0.1:9090")
        with mock.patch.object(constants, "ENABLE_CCXT_REQUESTS_COUNTER", True):
            async with _exchange_with_proxy_config(proxy_config, allow_request_counter=True) as exchange:
                await exchange.load_markets()
                assert _request_mock.call_count > 0
                assert all(
                    call.kwargs["proxy"] == "http://127.0.0.1:9090"
                    for call in _request_mock.call_args_list
                )
                assert isinstance(exchange.session, aiohttp_util.CounterClientSession)
                # requests are counted by session counter
                assert len(exchange.session.per_min.paths) > 0
                assert exchange.session.per_min.paths[next(iter(exchange.session.per_min.paths))] > 0
        _request_mock.reset_mock()

        # with http proxy callback
        proxy_config = exchanges.ExchangeProxyConfig(
            http_proxy_callback=lambda url, method, headers, body: "http://9.9.9.9:9090"
        )
        with mock.patch.object(constants, "ENABLE_CCXT_REQUESTS_COUNTER", True):
            async with _exchange_with_proxy_config(proxy_config, allow_request_counter=True) as exchange:
                await exchange.load_markets()
                assert _request_mock.call_count > 0
                assert all(
                    call.kwargs["proxy"] == "http://9.9.9.9:9090"
                    for call in _request_mock.call_args_list
                )
                assert isinstance(exchange.session, aiohttp_util.CounterClientSession)
                # requests are counted by session counter
                assert len(exchange.session.per_min.paths) > 0
                assert exchange.session.per_min.paths[next(iter(exchange.session.per_min.paths))] > 0
        _request_mock.reset_mock()


@contextlib.asynccontextmanager
async def _exchange_with_proxy_config(proxy_config: exchanges.ExchangeProxyConfig, allow_request_counter=False):
    exchange = None
    try:
        exchange = ccxt_client_util.instantiate_exchange(ccxt.kraken, {"enableRateLimit": False}, "test", proxy_config, allow_request_counter=allow_request_counter)
        yield exchange
    finally:
        if exchange:
            exchange.timeout_on_exit = 0    # avoid waiting for the exchange to close
            await exchange.close()


class TestSetSandboxMode:
    def _exchange_connector(self, *, raise_type_error: bool):
        client = mock.Mock()
        client.options = {}
        if raise_type_error:
            client.set_sandbox_mode.side_effect = TypeError("'NoneType' object is not iterable")
        else:
            client.set_sandbox_mode = mock.Mock()
        exchange_connector = mock.Mock()
        exchange_connector.client = client
        exchange_connector.name = "test-exchange"
        exchange_connector.logger = mock.Mock()
        exchange_connector.exchange_manager.exchange.uses_demo_trading_instead_of_sandbox.return_value = False
        return exchange_connector

    def test_type_error_when_sandboxed_raises_not_supported(self):
        exchange_connector = self._exchange_connector(raise_type_error=True)
        try:
            ccxt_client_util.set_sandbox_mode(exchange_connector, True)
            raise AssertionError("Expected ccxt.NotSupported")
        except ccxt.NotSupported as error:
            assert "test-exchange" in str(error)
            assert "sandbox/test URLs are unavailable" in str(error)
        exchange_connector.logger.warning.assert_called_once()
        warning_message = exchange_connector.logger.warning.call_args.args[0]
        assert "sandbox/test URLs are unavailable" in warning_message

    def test_type_error_when_not_sandboxed_is_ignored(self):
        exchange_connector = self._exchange_connector(raise_type_error=True)
        result = ccxt_client_util.set_sandbox_mode(exchange_connector, False)
        assert result is None
        exchange_connector.logger.warning.assert_not_called()

    def test_not_supported_is_re_raised_with_clear_message(self):
        exchange_connector = self._exchange_connector(raise_type_error=False)
        exchange_connector.client.set_sandbox_mode.side_effect = ccxt.NotSupported("sandbox mode")
        try:
            ccxt_client_util.set_sandbox_mode(exchange_connector, True)
            raise AssertionError("Expected ccxt.NotSupported")
        except ccxt.NotSupported as error:
            assert "test-exchange" in str(error)
            assert "sandbox/test URLs are unavailable" in str(error)
        exchange_connector.logger.warning.assert_called_once()
