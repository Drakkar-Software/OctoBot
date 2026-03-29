# OctoBot Node — Infrastructure

Deploys an inventory of OctoBot Node instances with zero-downtime rolling updates.

**Stack per node:** OctoBot Node + optional Nginx (reverse proxy) + optional Tor (SOCKS5 proxy) + optional PostgreSQL (on master)

## Prerequisites

- Python 3.10+ with pip (`pip install -r infra/node/requirements.txt` installs `ansible-core`)
- SSH access to target nodes (key-based, user `deploy` with sudo)
- OctoBot Docker image (`drakkarsoftware/octobot`) — the node runs via `OctoBot node` CLI command

## Quick start

```bash
# 1. Install Ansible
pip install -r infra/node/requirements.txt
cd infra/node/ansible

# 2. Install Ansible Galaxy roles and collections
ansible-galaxy install -r requirements.yml
ansible-galaxy collection install -r requirements.yml

# 3. Set up inventory
cp inventories/hosts.yml.example inventories/hosts.yml
vim inventories/hosts.yml                         # node IPs
vim inventories/group_vars/all/vars.yml           # secrets and overrides

# 4. Deploy
ansible-playbook playbooks/site.yml --private-key ~/.ssh/id_ed25519
```

## Playbooks

| Playbook | Purpose | When to use |
|---|---|---|
| `site.yml` | Full stack deploy (rolling, one node at a time) | First deploy, config changes, adding features |
| `deploy-octobot-node.yml` | Fast app-only update (pull + restart OctoBot) | After CI pushes a new Docker image |

### Examples

```bash
# Full deploy
ansible-playbook playbooks/site.yml --private-key ~/.ssh/id_ed25519

# Fast app-only update
ansible-playbook playbooks/deploy-octobot-node.yml --private-key ~/.ssh/id_ed25519

# Deploy a single node
ansible-playbook playbooks/site.yml --limit node-master-1.example.com

# Dry run (check mode)
ansible-playbook playbooks/site.yml --check --diff

# Pass secrets via extra-vars
ansible-playbook playbooks/site.yml \
  --extra-vars "secret_key=mykey admin_password=mypass"
```

## Configuration Reference

Shared defaults live in `roles/octobot/defaults/main.yml`. Overrides go in `inventories/group_vars/all/vars.yml`. Secrets can be passed via `--extra-vars` or set in the vars file.

### Feature Flags

| Variable | Default | Description |
|---|---|---|
| `enable_hardening` | `false` | Apply OS and SSH hardening via [devsec.hardening](https://github.com/dev-sec/ansible-collection-hardening) |
| `enable_tor` | `false` | Build and deploy a Tor SOCKS5 proxy sidecar; routes exchange traffic through Tor |
| `enable_replica_mode` | `false` | Deploy PostgreSQL on master, connect all nodes via `SCHEDULER_POSTGRES_URL` |
| `enable_nginx` | `false` | Deploy Nginx reverse proxy with SSL termination in front of OctoBot |
| `expose_web_ui` | `false` | Expose the OctoBot web UI (port 5001). When `false`, only the Node API port is exposed and nginx returns 403 for web routes |
| `disable_telemetry` | `false` | Disable Sentry telemetry by clearing `SENTRY_DSN` |
| `custom_tentacles_zip` | `""` | Path (local or URL) to a tentacles ZIP to install into OctoBot via Ansible |
| `additional_tentacles_package_url` | `""` | Comma-separated URLs for additional tentacles packages (set as `ADDITIONAL_TENTACLES_PACKAGE_URL` env var, OctoBot installs at startup on top of defaults) |
| `install_default_tentacles` | `true` | When `false`, skip default tentacles and only install from `additional_tentacles_package_url` |

### Secrets

Secrets are passed as Ansible variables (via `--extra-vars`, `vars.yml`, or any other Ansible variable source):

| Variable | Description |
|---|---|
| `secret_key` | JWT secret for the Node API |
| `admin_username` | Admin email (enforced non-default in production) |
| `admin_password` | Admin password (enforced non-default in production) |
| `postgres_password` | PostgreSQL password (only when `enable_replica_mode: true`) |

Optional task encryption keys:

| Variable | Description |
|---|---|
| `tasks_inputs_rsa_private_key` | RSA private key for decrypting task inputs |
| `tasks_inputs_ecdsa_public_key` | ECDSA public key for verifying task inputs |
| `tasks_outputs_rsa_public_key` | RSA public key for encrypting task outputs |
| `tasks_outputs_ecdsa_private_key` | ECDSA private key for signing task outputs |

### Hardening Details

When `enable_hardening: true`, the following [devsec.hardening](https://github.com/dev-sec/ansible-collection-hardening) roles are applied:

- **`devsec.hardening.os_hardening`** — kernel parameter hardening, SUID/SGID enforcement, password policies, core dump prevention
- **`devsec.hardening.ssh_hardening`** — disables root login, password auth, TCP/agent/X11 forwarding; enforces pubkey-only auth

> **Note:** `devsec.hardening.nginx_hardening` is **not** used because nginx runs inside a Docker container. Nginx security hardening (TLS 1.2+, security headers, rate limiting, `server_tokens off`) is applied directly via the `nginx.conf.j2` template.

Key overridable variables for hardening (set in group_vars):

```yaml
# OS hardening
os_auditd_enabled: true        # enable auditd
os_selinux_enabled: false      # SELinux (disable on most VPS)

# SSH hardening
ssh_permit_root_login: "no"
ssh_server_password_login: false
ssh_max_auth_retries: 3
ssh_allow_tcp_forwarding: "no"
ssh_x11_forwarding: false
```

### Inventory Groups

Two topology modes are supported:

- **Standalone (0 masters):** All hosts go in `octobot_nodes` directly (not in `master_nodes` or `consumer_nodes`). Each node runs independently with SQLite. No PostgreSQL is deployed.
- **Replica (1 master + N consumers):** Exactly **one** host in `master_nodes`, one or more in `consumer_nodes`. Requires `enable_replica_mode: true`. The master runs PostgreSQL + OctoBot (`--master`). Consumers run OctoBot (`--consumer_only`) connecting to the master's PostgreSQL.

> **Constraint:** At most 1 master node is allowed. The playbooks enforce this at startup and will fail with a clear error if 2+ masters are defined.

### Single Node vs Replica Mode

**Standalone** (default): Hosts in `octobot_nodes` only (no `master_nodes` or `consumer_nodes`). Each node uses SQLite for task scheduling. No PostgreSQL.

**Replica mode** (`enable_replica_mode: true`): Exactly one master runs PostgreSQL + OctoBot. Consumer nodes run OctoBot only, connecting to the master's PostgreSQL over the network. Firewall rules automatically allow port 5432 from consumer IPs to the master.

```yaml
# hosts.yml for replica mode
all:
  children:
    octobot_nodes:
      children:
        master_nodes:
          hosts:
            node-master-1.example.com:
              ansible_host: 10.0.0.1
              ansible_user: deploy
        consumer_nodes:
          hosts:
            node-consumer-1.example.com:
              ansible_host: 10.0.0.2
              ansible_user: deploy
            node-consumer-2.example.com:
              ansible_host: 10.0.0.3
              ansible_user: deploy
```

### Tor Proxy

When `enable_tor: true`, a custom Tor SOCKS5 proxy container (Alpine-based, ~8MB) is built and deployed alongside OctoBot. The environment variable `EXCHANGE_SOCKS_PROXY_AUTHENTICATED_URL=socks5h://tor:9050` routes all exchange (CCXT) traffic through the Tor network. The `USE_AUTHENTICATED_EXCHANGE_REQUESTS_ONLY_PROXY=False` flag ensures both authenticated and public requests are proxied.

### Custom Tentacles

Two approaches for installing custom tentacles:

**Approach 1: URL-based (recommended)** — OctoBot installs at startup, additive on top of defaults:

```yaml
# Single URL
additional_tentacles_package_url: "https://example.com/tentacles/my-tentacles.zip"

# Multiple URLs (comma-separated), VERSION_PLACEHOLDER is replaced by OctoBot version
additional_tentacles_package_url: "https://example.com/tentacles/VERSION_PLACEHOLDER/pkg.zip,https://other.com/extra.zip"

# Skip default tentacles entirely — only install from the URLs above
install_default_tentacles: false
```

**Approach 2: ZIP file via Ansible** — copied/downloaded to the host, installed after stack start:

```yaml
# Local file (copied to host via Ansible)
custom_tentacles_zip: "/path/to/my-tentacles.zip"

# Remote URL (downloaded on the host)
custom_tentacles_zip: "https://example.com/tentacles/my-tentacles.zip"
```

Both approaches can be combined. When no custom tentacles are configured, OctoBot installs the default official tentacles on first boot.

### Telemetry

Set `disable_telemetry: true` to clear the `SENTRY_DSN` environment variable, which prevents the Sentry error tracking client from initializing.

## Adding a Node

1. Add the host to `inventories/hosts.yml` under `master_nodes` or `consumer_nodes`
2. Deploy: `ansible-playbook playbooks/site.yml --limit <new-host>`

## SSH Keys

```bash
# Generate a key for your nodes
ssh-keygen -t ed25519 -f ~/.ssh/octobot_node -N ""
ssh-copy-id -i ~/.ssh/octobot_node.pub deploy@<node-ip>

# Use it with the playbook
ansible-playbook playbooks/site.yml --private-key ~/.ssh/octobot_node
```
