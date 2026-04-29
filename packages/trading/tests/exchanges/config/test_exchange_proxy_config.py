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
import mock
import pytest

import octobot_commons.proxy_config as commons_proxy_config
import octobot_commons.tests.test_config as test_config
import octobot_trading.constants as trading_constants
import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.config.exchange_proxy_config as exchange_proxy_config

from tests.exchanges import (
    DEFAULT_EXCHANGE_NAME,
    backtesting_config,
    backtesting_exchange_manager,
    fake_backtesting,
)

pytestmark = pytest.mark.asyncio


def _uninitialized_exchange_manager():
    """
    ExchangeManager after __init__ only: create_exchanges / initialize_impl was never run,
    so exchange is still None.
    """
    exchange_manager = exchanges.ExchangeManager(test_config.load_test_config(), DEFAULT_EXCHANGE_NAME)
    assert exchange_manager.exchange is None
    return exchange_manager


class TestExchangeProxyConfig:
    def test_defaults_match_trading_constants(self):
        config = exchange_proxy_config.ExchangeProxyConfig()
        assert config.aiohttp_trust_env == trading_constants.ENABLE_EXCHANGE_HTTP_PROXY_FROM_ENV
        assert config.stop_proxy_callback is None
        assert config.use_authenticated_exchange_requests_only_proxy is False
        assert isinstance(config, commons_proxy_config.ProxyConfig)


class TestDefaultEnvVarConfig:
    def test_reads_constants(self):
        with mock.patch.multiple(
            "octobot_trading.constants",
            EXCHANGE_HTTP_PROXY_AUTHENTICATED_URL="http://http-proxy:8080",
            EXCHANGE_HTTPS_PROXY_AUTHENTICATED_URL="https://https-proxy:8443",
            EXCHANGE_SOCKS_PROXY_AUTHENTICATED_URL="socks5://socks-proxy:1080",
            EXCHANGE_WS_PROXY_AUTHENTICATED_URL="ws://ws-proxy:8081",
            EXCHANGE_WSS_PROXY_AUTHENTICATED_URL="wss://wss-proxy:8444",
            EXCHANGE_WS_SOCKS_PROXY_AUTHENTICATED_URL="socks5://ws-socks:1081",
            USE_AUTHENTICATED_EXCHANGE_REQUESTS_ONLY_PROXY=True,
        ):
            config = exchange_proxy_config.ExchangeProxyConfig.default_env_var_config()
        assert config.http_proxy == "http://http-proxy:8080"
        assert config.https_proxy == "https://https-proxy:8443"
        assert config.socks_proxy == "socks5://socks-proxy:1080"
        assert config.ws_proxy == "ws://ws-proxy:8081"
        assert config.wss_proxy == "wss://wss-proxy:8444"
        assert config.ws_socks_proxy == "socks5://ws-socks:1081"
        assert config.use_authenticated_exchange_requests_only_proxy is True

    async def test_with_exchange_manager_calls_initialize(self, backtesting_exchange_manager):
        with mock.patch.object(
            exchange_proxy_config.ExchangeProxyConfig,
            "initialize",
            autospec=True,
        ) as initialize_mock:
            exchange_proxy_config.ExchangeProxyConfig.default_env_var_config(backtesting_exchange_manager)
        initialize_mock.assert_called_once_with(mock.ANY, backtesting_exchange_manager)


class TestInitialize:
    async def test_static_rest_proxy_logs_enabled(self, backtesting_exchange_manager):
        config = exchange_proxy_config.ExchangeProxyConfig(
            http_proxy="http://127.0.0.1:9090",
            use_authenticated_exchange_requests_only_proxy=False,
        )
        mock_logger = mock.Mock()
        with mock.patch.object(config, "_get_logger", return_value=mock_logger):
            config.initialize(backtesting_exchange_manager)
        mock_logger.info.assert_any_call(f"Enabled [{DEFAULT_EXCHANGE_NAME}] proxy")

    async def test_websocket_proxy_logs_enabled(self, backtesting_exchange_manager):
        config = exchange_proxy_config.ExchangeProxyConfig(
            wss_proxy="wss://127.0.0.1:9443",
        )
        mock_logger = mock.Mock()
        with mock.patch.object(config, "_get_logger", return_value=mock_logger):
            config.initialize(backtesting_exchange_manager)
        mock_logger.info.assert_any_call(f"Enabled [{DEFAULT_EXCHANGE_NAME}] websocket proxy")

    def test_static_rest_proxy_logs_enabled_when_exchange_not_set(self):
        uninitialized_manager = _uninitialized_exchange_manager()
        config = exchange_proxy_config.ExchangeProxyConfig(
            http_proxy="http://127.0.0.1:9090",
            use_authenticated_exchange_requests_only_proxy=False,
        )
        mock_logger = mock.Mock()
        with mock.patch.object(config, "_get_logger", return_value=mock_logger):
            config.initialize(uninitialized_manager)
        mock_logger.info.assert_any_call(f"Enabled [{DEFAULT_EXCHANGE_NAME}] proxy")

    def test_websocket_proxy_logs_enabled_when_exchange_not_set(self):
        uninitialized_manager = _uninitialized_exchange_manager()
        config = exchange_proxy_config.ExchangeProxyConfig(
            wss_proxy="wss://127.0.0.1:9443",
        )
        mock_logger = mock.Mock()
        with mock.patch.object(config, "_get_logger", return_value=mock_logger):
            config.initialize(uninitialized_manager)
        mock_logger.info.assert_any_call(f"Enabled [{DEFAULT_EXCHANGE_NAME}] websocket proxy")

    async def test_authenticated_only_http_replaces_with_callback(self, backtesting_exchange_manager):
        proxy_url = "http://auth-proxy:8080"
        config = exchange_proxy_config.ExchangeProxyConfig(
            http_proxy=proxy_url,
            use_authenticated_exchange_requests_only_proxy=True,
        )
        mock_logger = mock.Mock()
        # Keep patches active for callback invocations (closure calls exchange.is_authenticated_request).
        with mock.patch.object(
            backtesting_exchange_manager.exchange,
            "is_authenticated_request",
            mock.Mock(return_value=True),
        ), mock.patch.object(config, "_get_logger", return_value=mock_logger):
            config.initialize(backtesting_exchange_manager)
            assert config.http_proxy is None
            http_proxy_callback = config.http_proxy_callback
            get_proxy_url = config.get_proxy_url
            get_last_proxied_request_url = config.get_last_proxied_request_url
            assert http_proxy_callback is not None
            assert get_proxy_url is not None
            assert get_last_proxied_request_url is not None
            assert get_proxy_url() == proxy_url
            assert get_last_proxied_request_url() is None
            resolved_proxy = http_proxy_callback("https://api.example/private", "GET", {}, None)
            assert resolved_proxy == proxy_url
            assert get_last_proxied_request_url() == "https://api.example/private"

    async def test_authenticated_only_https_used_when_no_http(self, backtesting_exchange_manager):
        proxy_url = "https://auth-https:8443"
        config = exchange_proxy_config.ExchangeProxyConfig(
            https_proxy=proxy_url,
            use_authenticated_exchange_requests_only_proxy=True,
        )
        mock_logger = mock.Mock()
        with mock.patch.object(
            backtesting_exchange_manager.exchange,
            "is_authenticated_request",
            mock.Mock(return_value=False),
        ), mock.patch.object(config, "_get_logger", return_value=mock_logger):
            config.initialize(backtesting_exchange_manager)
            assert config.https_proxy is None
            https_proxy_callback = config.https_proxy_callback
            assert https_proxy_callback is not None
            assert https_proxy_callback("https://public", "GET", {}, None) is None

    async def test_authenticated_only_socks_used_when_no_http_nor_https(self, backtesting_exchange_manager):
        proxy_url = "socks5://127.0.0.1:1080"
        config = exchange_proxy_config.ExchangeProxyConfig(
            socks_proxy=proxy_url,
            use_authenticated_exchange_requests_only_proxy=True,
        )
        with mock.patch.object(
            backtesting_exchange_manager.exchange,
            "is_authenticated_request",
            mock.Mock(return_value=True),
        ), mock.patch.object(config, "_get_logger", return_value=mock.Mock()):
            config.initialize(backtesting_exchange_manager)
            assert config.socks_proxy is None
            socks_proxy_callback = config.socks_proxy_callback
            assert socks_proxy_callback is not None
            assert socks_proxy_callback("https://signed", "POST", {}, b"{}") == proxy_url


class TestCreateCallback:
    async def test_not_implemented_falls_back_to_static_proxy(self, backtesting_exchange_manager):
        proxy_url = "http://fallback-proxy:8080"
        config = exchange_proxy_config.ExchangeProxyConfig(
            http_proxy=proxy_url,
            use_authenticated_exchange_requests_only_proxy=True,
        )
        mock_logger = mock.Mock()
        with mock.patch.object(
            backtesting_exchange_manager.exchange,
            "is_authenticated_request",
            mock.Mock(side_effect=NotImplementedError),
        ), mock.patch.object(config, "_get_logger", return_value=mock_logger):
            config.initialize(backtesting_exchange_manager)
            http_proxy_callback = config.http_proxy_callback
            assert http_proxy_callback is not None
            assert http_proxy_callback("https://any", "GET", {}, None) == proxy_url
            mock_logger.warning.assert_called()

    async def test_when_exchange_stopped_returns_none(self, backtesting_exchange_manager):
        backtesting_exchange_manager.exchange = None
        proxy_url = "http://stopped-proxy:8080"
        config = exchange_proxy_config.ExchangeProxyConfig(
            http_proxy=proxy_url,
            use_authenticated_exchange_requests_only_proxy=True,
        )
        mock_logger = mock.Mock()
        with mock.patch.object(config, "_get_logger", return_value=mock_logger):
            config.initialize(backtesting_exchange_manager)
            http_proxy_callback = config.http_proxy_callback
            assert http_proxy_callback is not None
            assert http_proxy_callback("https://api", "GET", {}, None) is None
            mock_logger.warning.assert_called()


class TestStop:
    def test_invokes_callback_and_clears_proxies(self):
        stop_callback = mock.Mock()
        config = exchange_proxy_config.ExchangeProxyConfig(
            http_proxy_callback=lambda *_args: "http://x",
            stop_proxy_callback=stop_callback,
        )
        config.get_last_proxied_request_url = mock.Mock()
        config.get_proxy_url = mock.Mock()
        config.stop()
        stop_callback.assert_called_once_with()
        assert config.stop_proxy_callback is None
        assert config.http_proxy_callback is None
        assert config.get_last_proxied_request_url is None
        assert config.get_proxy_url is None
        assert config.proxy_host == commons_proxy_config.DEFAULT_PROXY_HOST
