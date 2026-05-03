# OctoBot Tunnel
[![Telegram](https://img.shields.io/badge/Telegram-grey.svg?logo=telegram)](https://t.me/OctoBot_Project)
[![Twitter](https://img.shields.io/twitter/follow/DrakkarsOctobot.svg?label=twitter&style=social)](https://x.com/DrakkarsOctoBot)

Python client for [Piko](https://github.com/andydunstall/piko) — an open-source reverse proxy (Ngrok alternative) that lets services behind firewalls register outbound-only tunnels.

This package is a full Python reimplementation of the official Go SDK (`github.com/andydunstall/piko/client`), using `asyncio` and `aiohttp`. It reproduces every feature of the Go client with identical behaviour.

This project is related to [OctoBot](https://github.com/Drakkar-Software/OctoBot).

---

## How Piko works

Upstream services open an outbound WebSocket connection to the Piko server and declare which **endpoint** they are listening on. The Piko server multiplexes incoming external connections back through that tunnel using [yamux](https://github.com/hashicorp/yamux). Services never need a public IP or open inbound port.

```
External client ──► Piko server (port 8000) ──► upstream tunnel ──► your service
                    Piko server (port 8001) ◄── WebSocket (outbound-only)
```

---

## Installation

```bash
pip install octobot-tunnel
```

Or add to your project's `requirements.txt`:

```
aiohttp>=3.9.5
```

---

## Usage

### Listen on an endpoint (Upstream)

Register a service as a Piko upstream and accept incoming connections as an `asyncio`-native stream:

```python
import asyncio
import octobot_tunnel

async def main():
    upstream = octobot_tunnel.Upstream(
        url="http://localhost:8001",
        token="my-api-token",       # optional JWT token
    )
    listener = await upstream.listen("my-endpoint")
    print("Listening on endpoint:", listener.endpoint_id())

    while True:
        conn = await listener.accept()
        asyncio.ensure_future(handle(conn))

async def handle(conn):
    data = await conn.read(4096)
    await conn.write(b"HTTP/1.1 200 OK\r\n\r\nHello from Piko!")
    await conn.close()

asyncio.run(main())
```

### Forward to a local service (ListenAndForward)

Transparently bridge all incoming Piko connections to a locally-running service:

```python
import asyncio
import octobot_tunnel

async def main():
    upstream = octobot_tunnel.Upstream(
        url="http://localhost:8001",
        token="my-api-token",
    )
    # All connections to "my-endpoint" are forwarded to localhost:3000
    forwarder = await upstream.listen_and_forward("my-endpoint", "localhost:3000")
    await forwarder.wait()

asyncio.run(main())
```

### Dial an endpoint (Dialer)

Open an outbound TCP connection to any registered Piko endpoint:

```python
import asyncio
import octobot_tunnel

async def main():
    dialer = octobot_tunnel.Dialer(
        url="http://localhost:8000",
        token="my-api-token",
    )
    conn = await dialer.dial("my-endpoint")
    await conn.write(b"hello")
    response = await conn.read(4096)
    print("Response:", response)
    await conn.close()

asyncio.run(main())
```

---

## API Reference

### `Upstream`

Manages listening on Piko upstream endpoints.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url` | `str \| None` | `http://localhost:8001` | Piko upstream port URL |
| `token` | `str \| None` | `None` | JWT bearer token for authentication |
| `tenant_id` | `str \| None` | `None` | Tenant identifier (experimental) |
| `tls_context` | `ssl.SSLContext \| None` | `None` | TLS configuration |
| `proxy_url` | `str \| None` | `None` | HTTP proxy URL |
| `min_reconnect_backoff` | `float` | `0.1` | Minimum reconnect delay in seconds |
| `max_reconnect_backoff` | `float` | `15.0` | Maximum reconnect delay in seconds |
| `logger` | `Logger \| None` | `None` | Optional structured logger |

**Methods:**
- `async listen(endpoint_id: str) → Listener` — connect and return a listener
- `async listen_and_forward(endpoint_id: str, addr: str) → Forwarder` — connect and start forwarding in the background

---

### `Listener`

Accepts incoming connections for a Piko endpoint.

**Methods:**
- `async accept() → Stream` — wait for the next incoming connection
- `async accept_with_context(stop_event: asyncio.Event) → Stream` — like `accept()`, stops when the event is set
- `addr() → PikoAddr` — returns `PikoAddr(network="tcp", address=endpoint_id)`
- `endpoint_id() → str` — the registered endpoint name
- `async close()` — send GoAway (stop accepting new connections, keep established streams open)
- `async shutdown()` — close the underlying yamux session (terminates all streams)

On transient disconnections, `accept()` automatically reconnects using the `Upstream`'s backoff configuration, identical to the Go client.

---

### `Dialer`

Opens TCP connections to Piko endpoints via the proxy port.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url` | `str \| None` | `http://localhost:8000` | Piko proxy port URL |
| `token` | `str \| None` | `None` | JWT bearer token |
| `tls_context` | `ssl.SSLContext \| None` | `None` | TLS configuration |

**Methods:**
- `async dial(endpoint_id: str) → Stream` — open a connection to the endpoint

---

### `Forwarder`

Created by `Upstream.listen_and_forward()`. Runs in the background.

**Methods:**
- `async wait()` — block until the forwarder stops
- `async close()` — stop accepting new connections and cancel active forwards

---

### `Stream`

Returned by `Listener.accept()` and `Dialer.dial()`.

**Methods:**
- `async read(n: int = -1) → bytes`
- `async write(data: bytes) → None`
- `async close() → None`

---

### Exceptions

| Exception | Description |
|---|---|
| `ConnectionClosed` | Operation on a closed connection or listener |
| `RetryableError` | Transient server error (HTTP 408/429/500/502/503/504) |
| `PikoError` | Base class for all tunnel exceptions |

---

## Protocol details

- **Transport:** WebSocket (via `aiohttp`)
  - Upstream connects to `ws(s)://host:8001/piko/v1/upstream/{endpoint_id}`
  - Dialer connects to `ws(s)://host:8000/_piko/v1/tcp/{endpoint_id}`
- **Multiplexing:** [yamux](https://github.com/hashicorp/yamux) client session over the WebSocket stream
- **Authentication:** `Authorization: Bearer <token>` header; optional `x-piko-tenant-id` header
- **Reconnection:** exponential backoff with 10% jitter (default: 100 ms → 15 s), retrying on transient HTTP errors

---

## Development

```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio

# Run all 138 tests
pytest tests/
```

### Test coverage

| Module | Tests |
|---|---|
| `yamux/frame.py` | 31 — encode/decode all frame types, flags, round-trips |
| `yamux/stream.py` | 15 — read/write, flow-control window, FIN/RST |
| `yamux/session.py` | 16 — accept, data dispatch, ping/pong, GoAway, concurrency |
| `client/backoff.py` | 7 — jitter range, doubling, cap, infinite/limited retries |
| `client/websocket.py` | 14 — auth headers, binary buffering, retryable status codes, TLS/proxy |
| `client/upstream.py` | 13 — URL construction, retry logic, config forwarding |
| `client/listener.py` | 14 — accept, reconnect, close vs shutdown, addr |
| `client/dialer.py` | 13 — URL construction, dial, config forwarding |
| `client/forwarder.py` | 11 — bidirectional copy, wait/close, connection refused |
