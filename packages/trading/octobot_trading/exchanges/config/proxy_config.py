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
import dataclasses
import typing
import octobot_trading.constants


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
    proxy_host: str = "DEFAULT PROXY HOST"

    @classmethod
    def default_env_var_config(cls):
        return cls(
            http_proxy=octobot_trading.constants.EXCHANGE_HTTP_PROXY_AUTHENTICATED_URL or None,
            https_proxy=octobot_trading.constants.EXCHANGE_HTTPS_PROXY_AUTHENTICATED_URL or None,
            socks_proxy=octobot_trading.constants.EXCHANGE_SOCKS_PROXY_AUTHENTICATED_URL or None,
            ws_proxy=octobot_trading.constants.EXCHANGE_WS_PROXY_AUTHENTICATED_URL or None,
            wss_proxy=octobot_trading.constants.EXCHANGE_WSS_PROXY_AUTHENTICATED_URL or None,
            ws_socks_proxy=octobot_trading.constants.EXCHANGE_WS_SOCKS_PROXY_AUTHENTICATED_URL or None,
        )
    
    def has_rest_proxy(self) -> bool:
        return bool(
            self.http_proxy or self.https_proxy or self.socks_proxy or 
            self.http_proxy_callback or self.https_proxy_callback or self.socks_proxy_callback
        )
    
    def has_websocket_proxy(self) -> bool:
        return bool(self.ws_proxy or self.wss_proxy or self.ws_socks_proxy)
    
    def has_proxy(self) -> bool:
        return self.has_rest_proxy() or self.has_websocket_proxy()
