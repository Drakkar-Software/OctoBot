# pylint: disable=too-many-instance-attributes
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
import typing
import dataclasses
SOCKS_PROXY_AVAILABLE = False  # pylint: disable=invalid-name
try:
    import aiohttp_socks
    SOCKS_PROXY_AVAILABLE = True  # pylint: disable=invalid-name
except ImportError:
    pass


DEFAULT_PROXY_HOST = "DEFAULT PROXY HOST"


def parse_socks_proxy_url_for_connector(proxy_url: str) -> typing.Tuple[bool, str]:
    """
    Split a SOCKS proxy URL into reverse-DNS flag and URL for aiohttp_socks.ProxyConnector.from_url.

    socks5h:// means the proxy resolves hostnames remotely (reverse DNS). aiohttp_socks expects
    socks5:// with rdns=True in that case.
    """
    reverse_dns = proxy_url.startswith('socks5h://')
    selected_proxy_url = (
        proxy_url if not reverse_dns else proxy_url.replace('socks5h://', 'socks5://')
    )
    return reverse_dns, selected_proxy_url


@dataclasses.dataclass
class ProxyConfig:
    """
    Proxy configuration class.
    """
    # REST proxy
    http_proxy: typing.Optional[str] = None
    http_proxy_callback: typing.Optional[
        typing.Callable[[str, str, dict, typing.Any], typing.Optional[str]]
    ] = None
    https_proxy: typing.Optional[str] = None
    https_proxy_callback: typing.Optional[
        typing.Callable[[str, str, dict, typing.Any], typing.Optional[str]]
    ] = None
    socks_proxy : typing.Optional[str] = None
    socks_proxy_callback: typing.Optional[
        typing.Callable[[str, str, dict, typing.Any], typing.Optional[str]]
    ] = None
    # Websocket proxy
    ws_proxy: typing.Optional[str] = None
    wss_proxy: typing.Optional[str] = None
    ws_socks_proxy: typing.Optional[str] = None
    # if set, returns the last url given to a callback method that return "True",
    # meaning the last url that used a proxy
    get_last_proxied_request_url: typing.Optional[
        typing.Callable[[], typing.Optional[str]]
    ] = None
    get_proxy_url: typing.Optional[typing.Callable[[], str]] = None
    # the host of this proxy, used to identify proxy connexion errors
    proxy_host: str = DEFAULT_PROXY_HOST
    _last_proxied_request_url: typing.Optional[str] = None

    def has_rest_proxy(self) -> bool:
        """
        Returns True if any rest proxy is set.
        """
        return bool(
            self.http_proxy or self.https_proxy or self.socks_proxy or
            self.http_proxy_callback or self.https_proxy_callback or self.socks_proxy_callback
        )

    def has_websocket_proxy(self) -> bool:
        """
        Returns True if any websocket proxy is set.
        """
        return bool(self.ws_proxy or self.wss_proxy or self.ws_socks_proxy)

    def has_proxy(self) -> bool:
        """
        Returns True if any proxy is set.
        """
        return self.has_rest_proxy() or self.has_websocket_proxy()

    def get_rest_proxy_url(self) -> typing.Optional[str]:
        """
        Returns the first rest proxy url that is set.
        Prioritizes https proxy, then http proxy.
        """
        return self.https_proxy or self.http_proxy

    def get_rest_socks_proxy_connector(self) -> "aiohttp_socks.ProxyConnector":
        """
        Returns the socks proxy connector that is set.
        """
        return self._socks_proxy_factory(self.socks_proxy, "socks_proxy")

    def get_websocket_proxy_url(self) -> typing.Optional[str]:
        """
        Returns the first websocket proxy url that is set.
        Prioritizes wss proxy, then ws proxy.
        """
        return self.wss_proxy or self.ws_proxy

    def get_websocket_proxy_connector(self) -> "aiohttp_socks.ProxyConnector":
        """
        Returns the wss proxy connector that is set.
        """
        return self._socks_proxy_factory(self.wss_proxy, "wss_proxy")

    def _socks_proxy_factory(
        self, proxy_url: typing.Optional[str],
        proxy_type: str
    ) -> "aiohttp_socks.ProxyConnector":
        """
        Returns the socks proxy connector that is set.
        """
        if not SOCKS_PROXY_AVAILABLE:
            raise ImportError("aiohttp_socks is not available")
        if proxy_url is None:
            raise ValueError(f"{proxy_type} proxy url is not set")
        reverse_dns, selected_proxy_url = parse_socks_proxy_url_for_connector(proxy_url)
        return aiohttp_socks.ProxyConnector.from_url(
            selected_proxy_url,
            rdns=reverse_dns if reverse_dns else None,
        )

    def get_aiohttp_session_proxy_args(self) -> dict:
        """
        Returns the arguments for aiohttp.ClientSession to use the proxy.
        """
        if self.socks_proxy:
            return {
                "connector": self.get_rest_socks_proxy_connector(),
            }
        if self.has_rest_proxy():
            return {
                "proxy": self.get_rest_proxy_url(),
            }
        return {}
