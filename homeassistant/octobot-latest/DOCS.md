# Home Assistant Add-on: OctoBot DEV

## How to use

This add-on runs [OctoBot](https://github.com/Drakkar-Software/OctoBot), an
open-source cryptocurrency trading bot, from the official
`drakkarsoftware/octobot:latest` Docker image.

Click **OPEN WEB UI** (or go to `http://<host>:8000/app`) to reach the OctoBot
Node web interface. The web interface is served without a login by default;
configure exchanges, strategies and password protection from within OctoBot
itself once it's running.

> The Node web interface is being rolled out as OctoBot's default UI. If
> `/app` returns a 404 on your installed OctoBot version, the node web bundle
> isn't baked into that build yet — uncomment the `5001/tcp` port in this
> add-on's config and point the web UI button at
> `http://<host>:5001` (the classic dashboard) as a fallback.

## Configuration

### Option: `enable_node_api`

Enables OctoBot's Node API/web interface service on port 8000. Leave this on
unless you only need the classic dashboard on 5001.

### Option: `node_external_host` (optional)

External host (and port, if non-default) the Node sync/mobile features advertise
— set this when OctoBot is reached through a reverse proxy or a public hostname
different from the add-on's own address. Leave empty to keep OctoBot's default.

## Data persistence

OctoBot's user config, logs and backtesting data are stored under this add-on's
persistent `/data` folder, so they survive add-on updates and rebuilds.

Installed **tentacles are intentionally not persisted**: they are wiped on every
start, so OctoBot reinstalls a fresh default tentacles set each time the add-on
boots.

## Want a stable release instead?

Install the **OctoBot** add-on instead, which tracks
`drakkarsoftware/octobot:stable`.
