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
import typing
import dataclasses
import urllib.parse

import octobot_trading.constants
import octobot_commons.logging
if typing.TYPE_CHECKING:
    import octobot_trading.exchanges


DEFAULT_PROXY_HOST = "DEFAULT PROXY HOST"


@dataclasses.dataclass
class ProxyConfig:
    # REST proxy
    http_proxy: typing.Optional[str] = None
    http_proxy_callback: typing.Optional[typing.Callable[[str, str, dict, typing.Any], typing.Optional[str]]] = None
    https_proxy: typing.Optional[str] = None
    https_proxy_callback: typing.Optional[typing.Callable[[str, str, dict, typing.Any], typing.Optional[str]]] = None
    socks_proxy : typing.Optional[str] = None
    socks_proxy_callback: typing.Optional[typing.Callable[[str, str, dict, typing.Any], typing.Optional[str]]] = None
    # Websocket proxy
    ws_proxy: typing.Optional[str] = None
    wss_proxy: typing.Optional[str] = None
    ws_socks_proxy: typing.Optional[str] = None
    # enable trust_env in exchange's aiohttp.ClientSession
    aiohttp_trust_env: bool = octobot_trading.constants.ENABLE_EXCHANGE_HTTP_PROXY_FROM_ENV
    # if set, will be called when exchange stops
    stop_proxy_callback: typing.Optional[typing.Callable] = None
    # if set, returns the last url given to a callback method that return "True", meaning the last url that used a proxy
    get_last_proxied_request_url: typing.Optional[typing.Callable[[], typing.Optional[str]]] = None
    get_proxy_url: typing.Optional[typing.Callable[[], str]] = None
    # the host of this proxy, used to identify proxy connexion errors
    proxy_host: str = DEFAULT_PROXY_HOST
    use_authenticated_exchange_requests_only_proxy: bool = False
    _last_proxied_request_url: typing.Optional[str] = None

    @classmethod
    def default_env_var_config(
        cls,
        exchange_manager: typing.Optional["octobot_trading.exchanges.ExchangeManager"] = None
    ):
        instance = cls(
            http_proxy=octobot_trading.constants.EXCHANGE_HTTP_PROXY_AUTHENTICATED_URL or None,
            https_proxy=octobot_trading.constants.EXCHANGE_HTTPS_PROXY_AUTHENTICATED_URL or None,
            socks_proxy=octobot_trading.constants.EXCHANGE_SOCKS_PROXY_AUTHENTICATED_URL or None,
            ws_proxy=octobot_trading.constants.EXCHANGE_WS_PROXY_AUTHENTICATED_URL or None,
            wss_proxy=octobot_trading.constants.EXCHANGE_WSS_PROXY_AUTHENTICATED_URL or None,
            ws_socks_proxy=octobot_trading.constants.EXCHANGE_WS_SOCKS_PROXY_AUTHENTICATED_URL or None,
            use_authenticated_exchange_requests_only_proxy=octobot_trading.constants.USE_AUTHENTICATED_EXCHANGE_REQUESTS_ONLY_PROXY,
        )
        if exchange_manager:
            instance.initialize(exchange_manager)
        return instance

    def initialize(self, exchange_manager: "octobot_trading.exchanges.ExchangeManager"):
        if self.has_rest_proxy():
            if self.use_authenticated_exchange_requests_only_proxy:
                # switch proxy config to a callback based proxy config for authenticated requests only
                # requires an exchange that supports is_authenticated_request()
                if self.http_proxy:
                    self.http_proxy_callback = self._create_callback(exchange_manager, self.http_proxy)
                    self.http_proxy = None
                elif self.https_proxy:
                    self.https_proxy_callback = self._create_callback(exchange_manager, self.https_proxy)
                    self.https_proxy = None
                elif self.socks_proxy:
                    self.socks_proxy_callback = self._create_callback(exchange_manager, self.socks_proxy)
                    self.socks_proxy = None
            else:
                self._get_logger().info(f"Enabled [{exchange_manager.exchange.name}] proxy")
        if self.has_websocket_proxy():
            self._get_logger().info(f"Enabled [{exchange_manager.exchange.name}] websocket proxy")

    def stop(self):
        if self.stop_proxy_callback:
            self.stop_proxy_callback()
            self.stop_proxy_callback = None
        self.http_proxy_callback = None
        self.https_proxy_callback = None
        self.socks_proxy_callback = None
        self.ws_proxy_callback = None
        self.wss_proxy_callback = None
        self.ws_socks_proxy_callback = None
        self.get_last_proxied_request_url = None
        self.get_proxy_url = None
        self.proxy_host = DEFAULT_PROXY_HOST

    def _create_callback(
        self,
        exchange_manager: "octobot_trading.exchanges.ExchangeManager",
        proxy_url: str
    ) -> typing.Callable[[str, str, dict, typing.Any], typing.Optional[str]]:
        def proxy_callback(url: str, method: str, headers: dict, body) -> typing.Optional[str]:
            try:
                if exchange_manager.exchange.is_authenticated_request(url, method, headers, body):
                    # use proxy on for authenticated requests which need a proxy call
                    self._last_proxied_request_url = url
                    # authenticated request, return proxy url
                    return proxy_url
                self._last_proxied_request_url = None
                # not authenticated request, return None and don't use proxy
                return None
            except NotImplementedError:
                self._get_logger().warning(
                    f"is_authenticated_request is not implemented for {exchange_manager.exchange_name}, "
                    f"using a dynamic proxy is impossible. Either implement is_authenticated_request for "
                    f"{exchange_manager.exchange_name} or use a static proxy. Is used for all requests."
                )
                return proxy_url
            except AttributeError:
                if exchange_manager.exchange is None:
                    self._get_logger().warning("proxy_callback called after exchange manager stopped")
                    return None
                # should never happen, raise if it does
                raise
            # propagate any expected error (should never happen)
        self.get_last_proxied_request_url = lambda: self._last_proxied_request_url
        self.get_proxy_url = lambda: proxy_url
        self.proxy_host = urllib.parse.urlparse(proxy_url).netloc # netloc is host:port
        self._get_logger().info(f"Enabled [{exchange_manager.exchange_name}] authenticated only proxy via {proxy_url}")
        return proxy_callback
    
    def has_rest_proxy(self) -> bool:
        return bool(
            self.http_proxy or self.https_proxy or self.socks_proxy or 
            self.http_proxy_callback or self.https_proxy_callback or self.socks_proxy_callback
        )
    
    def has_websocket_proxy(self) -> bool:
        return bool(self.ws_proxy or self.wss_proxy or self.ws_socks_proxy)
    
    def has_proxy(self) -> bool:
        return self.has_rest_proxy() or self.has_websocket_proxy()

    def _get_logger(self) -> octobot_commons.logging.BotLogger:
        return octobot_commons.logging.get_logger(ProxyConfig.__name__)
