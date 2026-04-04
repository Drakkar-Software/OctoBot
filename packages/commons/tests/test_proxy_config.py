#  Drakkar-Software OctoBot-Commons
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
import asyncio
import mock
import pytest
import aiohttp

import octobot_commons.proxy_config as proxy_config


def _open_client_session_from_proxy_config(proxy_configuration, check_session):
    async def runner():
        session_kwargs = proxy_configuration.get_aiohttp_session_proxy_args()
        async with aiohttp.ClientSession(**session_kwargs) as client_session:
            check_session(client_session, session_kwargs)

    asyncio.run(runner())


class TestProxyConfigDefaults:
    def test_default_proxy_host_constant(self):
        empty_config = proxy_config.ProxyConfig()
        assert empty_config.proxy_host == proxy_config.DEFAULT_PROXY_HOST


class TestHasRestProxy:
    def test_false_when_unset(self):
        config = proxy_config.ProxyConfig()
        assert config.has_rest_proxy() is False

    def test_true_for_http_https_socks(self):
        assert proxy_config.ProxyConfig(http_proxy="http://h:1").has_rest_proxy() is True
        assert proxy_config.ProxyConfig(https_proxy="https://h:1").has_rest_proxy() is True
        assert proxy_config.ProxyConfig(socks_proxy="socks5://h:1").has_rest_proxy() is True

    def test_true_for_callbacks(self):
        dummy_callback = mock.Mock(return_value=None)
        assert proxy_config.ProxyConfig(http_proxy_callback=dummy_callback).has_rest_proxy() is True
        assert proxy_config.ProxyConfig(https_proxy_callback=dummy_callback).has_rest_proxy() is True
        assert proxy_config.ProxyConfig(socks_proxy_callback=dummy_callback).has_rest_proxy() is True


class TestHasWebsocketProxy:
    def test_false_when_unset(self):
        assert proxy_config.ProxyConfig().has_websocket_proxy() is False

    def test_true_for_ws_wss_ws_socks(self):
        assert proxy_config.ProxyConfig(ws_proxy="ws://h:1").has_websocket_proxy() is True
        assert proxy_config.ProxyConfig(wss_proxy="wss://h:1").has_websocket_proxy() is True
        assert proxy_config.ProxyConfig(ws_socks_proxy="socks5://h:1").has_websocket_proxy() is True


class TestHasProxy:
    def test_true_for_rest_or_websocket(self):
        rest_only = proxy_config.ProxyConfig(http_proxy="http://h:1")
        ws_only = proxy_config.ProxyConfig(ws_proxy="ws://h:1")
        assert rest_only.has_proxy() is True
        assert ws_only.has_proxy() is True

    def test_false_when_unset(self):
        assert proxy_config.ProxyConfig().has_proxy() is False


class TestGetRestProxyUrl:
    def test_prioritizes_https_over_http(self):
        config = proxy_config.ProxyConfig(
            http_proxy="http://a:1",
            https_proxy="https://b:2",
        )
        assert config.get_rest_proxy_url() == "https://b:2"

    def test_falls_back_to_http(self):
        config = proxy_config.ProxyConfig(http_proxy="http://a:1")
        assert config.get_rest_proxy_url() == "http://a:1"

    def test_none_when_unset(self):
        assert proxy_config.ProxyConfig().get_rest_proxy_url() is None


class TestGetWebsocketProxyUrl:
    def test_prioritizes_wss_over_ws(self):
        config = proxy_config.ProxyConfig(
            ws_proxy="ws://a:1",
            wss_proxy="wss://b:2",
        )
        assert config.get_websocket_proxy_url() == "wss://b:2"

    def test_falls_back_to_ws(self):
        config = proxy_config.ProxyConfig(ws_proxy="ws://a:1")
        assert config.get_websocket_proxy_url() == "ws://a:1"

    def test_none_when_unset(self):
        assert proxy_config.ProxyConfig().get_websocket_proxy_url() is None


class TestSocksProxyFactory:
    def test_raises_import_error_when_socks_unavailable(self):
        config = proxy_config.ProxyConfig()
        with mock.patch.object(proxy_config, "SOCKS_PROXY_AVAILABLE", False):
            with pytest.raises(ImportError, match="aiohttp_socks is not available"):
                config._socks_proxy_factory("socks5://h:1", "socks_proxy")

    def test_raises_when_url_missing(self):
        config = proxy_config.ProxyConfig()
        with mock.patch.object(proxy_config, "SOCKS_PROXY_AVAILABLE", True):
            with pytest.raises(ValueError, match="socks_proxy proxy url is not set"):
                config._socks_proxy_factory(None, "socks_proxy")

    def test_calls_from_url(self):
        if not proxy_config.SOCKS_PROXY_AVAILABLE:
            pytest.skip("aiohttp_socks is not installed")

        async def build_connector_in_running_loop():
            config = proxy_config.ProxyConfig()
            return config._socks_proxy_factory("socks5://host:1080", "socks_proxy")

        connector = asyncio.run(build_connector_in_running_loop())
        assert isinstance(connector, proxy_config.aiohttp_socks.ProxyConnector)


class TestGetRestSocksProxyConnector:
    def test_uses_socks_proxy_field(self):
        config = proxy_config.ProxyConfig(socks_proxy="socks5://r:1")
        with mock.patch.object(
            proxy_config.ProxyConfig,
            "_socks_proxy_factory",
            mock.Mock(return_value="connector-rest"),
        ) as factory_mock:
            assert config.get_rest_socks_proxy_connector() == "connector-rest"
        factory_mock.assert_called_once_with("socks5://r:1", "socks_proxy")


class TestGetWebsocketProxyConnector:
    def test_uses_wss_proxy_field(self):
        config = proxy_config.ProxyConfig(wss_proxy="socks5://w:1")
        with mock.patch.object(
            proxy_config.ProxyConfig,
            "_socks_proxy_factory",
            mock.Mock(return_value="connector-ws"),
        ) as factory_mock:
            assert config.get_websocket_proxy_connector() == "connector-ws"
        factory_mock.assert_called_once_with("socks5://w:1", "wss_proxy")


class TestGetAiohttpSessionProxyArgs:
    def test_empty(self):
        assert proxy_config.ProxyConfig().get_aiohttp_session_proxy_args() == {}

    def test_prefers_socks_over_http(self):
        config = proxy_config.ProxyConfig(
            socks_proxy="socks5://s:1",
            http_proxy="http://h:1",
        )
        fake_connector = object()
        with mock.patch.object(
            proxy_config.ProxyConfig,
            "get_rest_socks_proxy_connector",
            mock.Mock(return_value=fake_connector),
        ):
            session_args = config.get_aiohttp_session_proxy_args()
        assert session_args == {"connector": fake_connector}

    def test_rest_http_only(self):
        config = proxy_config.ProxyConfig(http_proxy="http://h:9")
        assert config.get_aiohttp_session_proxy_args() == {"proxy": "http://h:9"}

    def test_rest_https_url(self):
        config = proxy_config.ProxyConfig(https_proxy="https://h:9")
        assert config.get_aiohttp_session_proxy_args() == {"proxy": "https://h:9"}

    def test_rest_via_callback_only(self):
        callback = mock.Mock(return_value=None)
        config = proxy_config.ProxyConfig(http_proxy_callback=callback)
        assert config.get_aiohttp_session_proxy_args() == {"proxy": None}

    def test_creates_client_session_with_empty_proxy_kwargs(self):
        def check_session(client_session, session_kwargs):
            assert session_kwargs == {}
            assert isinstance(client_session, aiohttp.ClientSession)

        _open_client_session_from_proxy_config(proxy_config.ProxyConfig(), check_session)

    def test_creates_client_session_with_http_proxy_kwargs(self):
        http_proxy_url = "http://127.0.0.1:9"

        def check_session(client_session, session_kwargs):
            assert session_kwargs == {"proxy": http_proxy_url}
            assert isinstance(client_session, aiohttp.ClientSession)

        proxy_configuration = proxy_config.ProxyConfig(http_proxy=http_proxy_url)
        _open_client_session_from_proxy_config(proxy_configuration, check_session)

    def test_creates_client_session_with_https_proxy_kwargs(self):
        https_proxy_url = "https://127.0.0.1:9"

        def check_session(client_session, session_kwargs):
            assert session_kwargs == {"proxy": https_proxy_url}
            assert isinstance(client_session, aiohttp.ClientSession)

        proxy_configuration = proxy_config.ProxyConfig(https_proxy=https_proxy_url)
        _open_client_session_from_proxy_config(proxy_configuration, check_session)

    def test_creates_client_session_with_callback_only_proxy_kwargs(self):
        callback = mock.Mock(return_value=None)

        def check_session(client_session, session_kwargs):
            assert session_kwargs == {"proxy": None}
            assert isinstance(client_session, aiohttp.ClientSession)

        proxy_configuration = proxy_config.ProxyConfig(http_proxy_callback=callback)
        _open_client_session_from_proxy_config(proxy_configuration, check_session)

    def test_creates_client_session_with_socks_proxy_kwargs(self):
        if not proxy_config.SOCKS_PROXY_AVAILABLE:
            pytest.skip("aiohttp_socks is not installed")

        socks_url = "socks5://127.0.0.1:1080"

        def check_session(client_session, session_kwargs):
            socks_connector = session_kwargs["connector"]
            assert isinstance(socks_connector, proxy_config.aiohttp_socks.ProxyConnector)
            assert isinstance(client_session, aiohttp.ClientSession)
            assert client_session.connector is socks_connector

        proxy_configuration = proxy_config.ProxyConfig(socks_proxy=socks_url)
        _open_client_session_from_proxy_config(proxy_configuration, check_session)

    def test_creates_client_session_prefers_socks_connector_when_also_http_set(self):
        if not proxy_config.SOCKS_PROXY_AVAILABLE:
            pytest.skip("aiohttp_socks is not installed")

        def check_session(client_session, session_kwargs):
            assert "connector" in session_kwargs
            assert "proxy" not in session_kwargs
            socks_connector = session_kwargs["connector"]
            assert isinstance(socks_connector, proxy_config.aiohttp_socks.ProxyConnector)
            assert client_session.connector is socks_connector

        proxy_configuration = proxy_config.ProxyConfig(
            socks_proxy="socks5://127.0.0.1:1080",
            http_proxy="http://127.0.0.1:9",
        )
        _open_client_session_from_proxy_config(proxy_configuration, check_session)
