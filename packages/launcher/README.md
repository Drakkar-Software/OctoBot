# octobot-launcher

A lightweight, self-contained daemon that manages OctoBot trading-bot instances on a single host. It handles the full lifecycle — start, stop, update, restart — across three different runtimes, and exposes a local HTTP API that the bundled CLI (and mobile apps) talk to.

## Why it exists

Running OctoBot in production requires more than just `python start.py`. Instances need to survive reboots, recover after crashes, update themselves without manual SSH sessions, and be reachable from a phone without opening the host to the internet. The launcher solves all of that as a single static binary with no external runtime dependencies.

## How it works

The launcher runs as an OS service (systemd on Linux, launchd on macOS, SCM on Windows). On first boot it writes a one-time bootstrap token to disk, then starts a local HTTP API bound to `127.0.0.1:7531` by default. All subsequent management — from the CLI or a mobile app — goes through that API with bearer-token authentication.

Instances are stored as JSON records in the data directory. The launcher supervises them directly: it spawns processes, holds PIDs, sends signals on stop/restart, and optionally probes an HTTP health endpoint to track liveness. When a Docker instance is stopped or updated, the launcher calls the Docker daemon rather than managing a process itself. All three backends — Docker, native binary, and Python virtualenv — implement the same `Backend` trait, so the rest of the system doesn't need to know which one it's talking to.

## Getting started

Build the binary:

```sh
cargo build --release -p octobot-launcher-cli
```

Install as a system service:

```sh
octobot-launcher service install
octobot-launcher service start
```

On first start the bootstrap token is printed to stdout and written to `bootstrap_token.txt` in the data directory. Use it immediately to create a persistent token:

```sh
octobot-launcher token create --label my-token
```

The bootstrap token is automatically removed from the store after it is first used; the new token is what you keep.

## Instances

An instance represents one running OctoBot. Add one with the runtime of your choice:

```sh
# Docker (default image drakkar/octobot:<version>)
octobot-launcher instance add --name mybot --runtime docker --version 2.4.42

# Pre-built binary
octobot-launcher instance add --name mybot --runtime binary --version 2.4.42

# Python virtualenv (managed by the launcher)
octobot-launcher instance add --name mybot --runtime python --version 2.4.42
```

Starting an instance tells the supervisor to bring it up according to its runtime. Stopping it gracefully signals the process (or stops the container) and waits for the configured timeout before escalating to SIGKILL.

```sh
octobot-launcher instance start <id>
octobot-launcher instance stop  <id>
octobot-launcher instance status <id>
```

IDs can be abbreviated to their 8-character prefix shown in `instance list`.

## Auto-update

The launcher checks a signed manifest at regular intervals (default: every 6 hours). The manifest is verified with an Ed25519 key baked into the binary at build time, so a compromised distribution server cannot push malicious updates. When an update is available, the launcher replaces itself on disk using an atomic rename and schedules a restart.

Instance updates follow a blue-green pattern: pull the new image/binary, stop and remove the old container/process, start the new one. Downgrades are blocked unless explicitly requested.

```sh
octobot-launcher update check
octobot-launcher update apply
```

## Tokens and access control

Every API request requires a bearer token. Tokens carry a set of scopes (`instances:read`, `instances:write`, `updates:apply`, `tokens:manage`, etc.) and can have an expiry. The mobile-app pairing flow uses a QR code that encodes the API address and token together.

```sh
octobot-launcher token list
octobot-launcher token create --label ci-runner --scope instances:read,instances:write
octobot-launcher token revoke  <id>
octobot-launcher token rotate  <id>   # revoke old, issue new with same scopes
```

## Configuration

The launcher looks for a TOML file at the platform default location (`~/.config/OctoBotLauncher/config.toml` on Linux, `~/Library/Application Support/software.Drakkar.OctoBotLauncher/config.toml` on macOS). Any key can be overridden with an environment variable using the `OCTOBOT_LAUNCHER__` prefix and `__` as the section separator:

```sh
OCTOBOT_LAUNCHER__LAUNCHER__API_BIND=0.0.0.0:7531
OCTOBOT_LAUNCHER__UPDATE__CHANNEL=beta
```

The `octobot-launcher doctor` command checks that all backends are reachable, the data directory is writable, and at least one token is configured.

## Building

The workspace requires Rust 1.81 or later. The release profile produces a stripped, LTO-optimised binary:

```sh
cargo build --release -p octobot-launcher-cli
```

For cross-compiled targets (e.g. `aarch64-unknown-linux-musl`) use `cross`:

```sh
cross build --release -p octobot-launcher-cli --target aarch64-unknown-linux-musl
```
