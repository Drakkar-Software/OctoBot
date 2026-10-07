# Classic web interface: HTTPS and WebSockets

WebSocket server code lives under `web_interface/websockets/` (`server/`, `core/`, `protocol/`, `socket_namespaces/`). Flask HTTP is mounted via `web_interface/asgi/wsgi_to_asgi.py` (asgiref subclass, `thread_sensitive=False`) in `websockets/server/asgi_composite.py`.

## TLS at reverse proxy (recommended)

Terminate TLS on nginx, Caddy, or Traefik. OctoBot listens on plain HTTP on `CONFIG_WEB` port; browsers use `wss://` when the page is served over HTTPS (`octobot_websocket.js` selects `wss:` from `location.protocol`).

Proxy must forward WebSocket upgrades on the same host and path as the UI:

- `proxy_http_version 1.1`
- `proxy_set_header Upgrade $http_upgrade`
- `proxy_set_header Connection "upgrade"`
- Long read timeouts on `/dashboard`, `/notifications`, and other WS paths

## Environment variables

| Variable | Effect |
|----------|--------|
| `OCTOBOT_PROXY_FIX_SCRIPT_NAME=True` | `ProxyFix` `x_script_name` for subpath deploys; sets `WEB_SOCKET_BASE_PATH` for WS URLs |
| `OCTOBOT_PROXY_FIX_HTTPS=True` | `ProxyFix` `x_proto` and `x_host` so Flask sees HTTPS and correct cookies |

When either proxy-fix variable is enabled, the web interface logs an INFO line at startup describing which forwarded headers are trusted.

## Manual smoke checklist

- Dashboard profitability and candles update over HTTPS
- Notifications and bot lock behavior on `/notifications`
- Password-protected UI: WS rejected without login; works after login
- Subpath prefix included in WS URL when using script name proxy fix
