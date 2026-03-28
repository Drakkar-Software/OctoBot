---
title: Configuration
description: Configuring OctoBot Node — feature flags, secrets, resource limits, environment variables, and tentacle installation methods.
sidebar_position: 2
---

# Configuration

Node behavior is controlled through Ansible group variables defined in the inventory. These variables are rendered into a `.env` file and a `docker-compose.yml` at deploy time, so the running containers see them as standard environment variables.

## Feature flags

Feature flags toggle major capabilities on or off. All default to their most conservative setting — disabled or true for tentacle installation.

`enable_nginx` deploys an nginx reverse proxy in front of the OctoBot API with TLS termination, security headers, and rate limiting. When enabled, the OctoBot ports bind to `127.0.0.1` instead of `0.0.0.0`, so all external traffic flows through nginx.

`expose_web_ui` controls whether the React dashboard is accessible. When disabled and nginx is active, requests to the root path return 403. This is useful for headless nodes that only serve the API.

`enable_tor` adds a Tor SOCKS5 proxy sidecar. All exchange traffic from OctoBot is routed through the Tor network, anonymizing the node's IP address on outbound CCXT requests. The proxy listens on an isolated Docker network so only the OctoBot container can reach it.

`enable_replica_mode` switches from standalone SQLite to the master–consumer PostgreSQL topology. See [Overview](./overview.md#replica-mode) for how the topology works.

`enable_hardening` applies OS and SSH hardening via the devsec Ansible collection. See [Security](./security.md) for details.

`disable_telemetry` clears the Sentry DSN in the container environment, preventing error reports from leaving the node.

## Secrets

Several values must be set before deploying to production. The defaults are intentionally unusable to prevent accidental exposure.

`secret_key` is the JWT signing secret for the Node API. If left empty, the deployment generates one automatically, but this means every redeploy rotates the key and invalidates existing sessions.

`admin_username` and `admin_password` are the credentials for the admin account. The defaults (`admin@example.com` and empty) are rejected in production — set real values in `group_vars/all/vars.yml` or pass them via `--extra-vars`.

`postgres_password` is required when `enable_replica_mode` is true. Both the master's PostgreSQL container and the consumer connection strings use this value.

All secrets should be passed via `--extra-vars` on the command line or stored in an Ansible Vault-encrypted vars file rather than committed in plain text to the inventory.

### Task encryption

Task inputs and outputs can optionally be encrypted end-to-end using RSA for payload encryption and ECDSA for signature verification. There are two key pairs — one for the node side and one for the producer side — each with an RSA and an ECDSA component. When configured, the scheduler encrypts and signs task data before storing it, and consumers decrypt and verify before execution.

These keys are optional. When omitted, task data is stored and transmitted in plain text.

## Resource limits

Container memory limits prevent a single service from consuming all available RAM on the host.

| Service    | Default |
|------------|---------|
| OctoBot    | 2 GB    |
| PostgreSQL | 2 GB    |
| Nginx      | 256 MB  |
| Tor        | 256 MB  |

Override these in `group_vars/all/vars.yml` using `octobot_mem_limit`, `postgres_mem_limit`, `nginx_mem_limit`, and `tor_mem_limit`.

## Ports

| Port | Service    | Notes |
|------|------------|-------|
| 8000 | Node API   | Binds to `127.0.0.1` when nginx is enabled |
| 5001 | Web UI     | Only exposed when `expose_web_ui` is true |
| 80   | Nginx HTTP | Redirects to HTTPS |
| 443  | Nginx HTTPS| TLS termination |
| 5432 | PostgreSQL | Master only, replica mode |

## Tentacle installation

Tentacles can be installed through three methods, which can be combined.

**Default tentacles** are installed automatically on first boot. This is the standard set of exchange connectors, evaluators, and trading modes shipped with OctoBot. Disable this with `install_default_tentacles: false` if you only want custom tentacles.

**Ansible-managed ZIP** uses the `custom_tentacles_zip` variable, which accepts either a local file path or a URL. Ansible copies or downloads the ZIP to the host after the stack starts, then runs the tentacle installer inside the OctoBot container. This is useful for baking a known tentacle set into a deployment.

```yaml
# Local file
custom_tentacles_zip: "/path/to/my-tentacles.zip"

# Remote URL
custom_tentacles_zip: "https://artifacts.example.com/tentacles/v2.zip"
```

**Runtime URL installation** uses `additional_tentacles_package_url`. OctoBot itself fetches and installs from these URLs at startup, so no Ansible involvement is needed after the initial deploy. Multiple URLs can be comma-separated. This is the recommended method for tentacles that update independently of the infrastructure.

```yaml
additional_tentacles_package_url: "https://cdn.example.com/tentacles/latest.zip"
```
