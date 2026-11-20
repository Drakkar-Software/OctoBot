<!-- https://developers.home-assistant.io/docs/apps/presentation#keeping-a-changelog -->
<!-- Versions are now CI-generated from the core OctoBot release tag (see
     homeassistant/ci/addon-meta.sh) — one entry per core release, not per add-on build. -->

## 1.1.2

- Add optional `node_external_host` configuration option: sets the external host
  (and port, if non-default) the Node sync/mobile features advertise, for
  reverse-proxy / public-hostname setups. Leave empty to keep OctoBot's default.

## 1.1.1

- Rebuild against the current OctoBot base image.

## 1.1.0

- Tentacles are no longer persisted: they are wiped on every start so OctoBot
  reinstalls a fresh default tentacles set each boot. User config, logs and
  backtesting data still persist under `/data`.

## 1.0.0

- Initial release: wraps `drakkarsoftware/octobot:stable`, exposes the Node
  web interface on port 8000 with a web UI button, persists OctoBot data
  under `/data`.
