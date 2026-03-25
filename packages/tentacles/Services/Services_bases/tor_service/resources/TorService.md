Routes all exchange traffic through the Tor anonymity network using a local SOCKS5 proxy.

## Activation

Add a `tor` entry under `services` in your `user/config.json`:

```json
"services": {
  "tor": {
    "enabled": true,
    "binary-path": "tor",
    "socks-port": 9050,
    "http-port": 0,
    "control-port": 9051,
    "auto-update-torrc": false,
    "torrc-extra": ""
  }
}
```

Tor must be installed on the system (`apt install tor`, `brew install tor`, etc.). Set `binary-path` to the full path if `tor` is not on your `PATH`.

When `auto-update-torrc` is `true`, the service writes a minimal `torrc` to `~/.octobot/tor/generated_torrc` before starting Tor. Use `torrc-extra` to append custom directives (e.g. `ExitNodes {us}` to pin exit country).

The service attaches to an already-running Tor daemon if the SOCKS port is already open, so you can manage the Tor process externally if preferred.

## Exchange proxy

When TorService connects, it automatically applies its proxy config to all currently running exchanges via `trading_api.set_all_exchanges_proxy_config()`. Any exchange that has no existing proxy configured is routed through `socks5h://127.0.0.1:9050`. If an exchange already has a proxy configured (e.g. via environment variables), a warning is logged and Tor is not applied to it.

To request a fresh Tor identity (new exit node) at runtime:

```python
await tor_service.request_new_identity()
```
