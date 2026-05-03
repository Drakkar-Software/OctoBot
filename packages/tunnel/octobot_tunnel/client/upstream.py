import asyncio
import ssl
from typing import Optional
from urllib.parse import urlparse, urlunparse

from octobot_tunnel.client.backoff import Backoff
from octobot_tunnel.client.exceptions import RetryableError
from octobot_tunnel.client.listener import Listener
from octobot_tunnel.client.logger import Logger, NopLogger
from octobot_tunnel.client.websocket import dial_websocket
from octobot_tunnel.yamux.session import YamuxSession

_DEFAULT_UPSTREAM_URL = "http://localhost:8001"
_DEFAULT_MIN_RECONNECT_BACKOFF = 0.1   # seconds
_DEFAULT_MAX_RECONNECT_BACKOFF = 15.0  # seconds


class Upstream:
    """
    Manages listening on Piko upstream endpoints.

    Equivalent to the Go client's Upstream struct.

    The client establishes an outbound WebSocket connection to the Piko server
    and registers the endpoint. Incoming connections are multiplexed over this
    single outbound connection via yamux. The connection is automatically
    re-established on transient failures.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
        tenant_id: Optional[str] = None,
        tls_context: Optional[ssl.SSLContext] = None,
        proxy_url: Optional[str] = None,
        min_reconnect_backoff: float = _DEFAULT_MIN_RECONNECT_BACKOFF,
        max_reconnect_backoff: float = _DEFAULT_MAX_RECONNECT_BACKOFF,
        logger: Optional[Logger] = None,
    ):
        self.url = url
        self.token = token
        self.tenant_id = tenant_id
        self.tls_context = tls_context
        self.proxy_url = proxy_url
        self.min_reconnect_backoff = min_reconnect_backoff
        self.max_reconnect_backoff = max_reconnect_backoff
        self._log = logger

    async def listen(self, endpoint_id: str) -> Listener:
        """
        Listen for connections on the given endpoint.

        Connects synchronously (with retry/backoff). Returns a Listener that
        can be used to accept incoming connections.
        """
        session = await self._connect(endpoint_id)
        ln = Listener(endpoint_id, self)
        ln._attach_session(session)
        return ln

    async def listen_and_forward(self, endpoint_id: str, addr: str) -> "Forwarder":
        """
        Listen on endpoint and automatically forward each connection to addr.

        Starts a background Forwarder task. Returns immediately after the
        initial connection succeeds.
        """
        from octobot_tunnel.client.forwarder import Forwarder
        ln = await self.listen(endpoint_id)
        return Forwarder(ln, addr, self._logger())

    async def _connect(self, endpoint_id: str) -> YamuxSession:
        """
        Connect to the Piko server for the given endpoint, with retry/backoff.
        Returns a started YamuxSession.
        """
        min_bo = self.min_reconnect_backoff or _DEFAULT_MIN_RECONNECT_BACKOFF
        max_bo = self.max_reconnect_backoff or _DEFAULT_MAX_RECONNECT_BACKOFF
        boff = Backoff(retries=0, min_backoff=min_bo, max_backoff=max_bo)

        while True:
            url = self._listen_url(endpoint_id)
            self._logger().debug("connecting", endpoint_id=endpoint_id, url=url)
            try:
                transport = await dial_websocket(
                    url=url,
                    token=self.token,
                    tenant_id=self.tenant_id,
                    ssl_context=self.tls_context,
                    proxy_url=self.proxy_url,
                )
                self._logger().debug("connected", endpoint_id=endpoint_id, url=url)
                session = YamuxSession(transport)
                session.start()
                return session
            except RetryableError as exc:
                delay, _ = boff.backoff()
                self._logger().warning(
                    "connect failed; retrying",
                    endpoint_id=endpoint_id,
                    url=url,
                    backoff=f"{delay:.2f}s",
                    error=str(exc),
                )
                await asyncio.sleep(delay)
            except Exception as exc:
                self._logger().error(
                    "connect failed; non-retryable",
                    endpoint_id=endpoint_id,
                    url=url,
                    error=str(exc),
                )
                raise

    def _listen_url(self, endpoint_id: str) -> str:
        base = self.url or _DEFAULT_UPSTREAM_URL
        parsed = urlparse(base)
        scheme = {"http": "ws", "https": "wss"}.get(parsed.scheme, parsed.scheme)
        path = (parsed.path or "").rstrip("/") + f"/piko/v1/upstream/{endpoint_id}"
        return urlunparse((scheme, parsed.netloc, path, parsed.params, parsed.query, parsed.fragment))

    def _logger(self) -> Logger:
        return self._log if self._log is not None else NopLogger()
