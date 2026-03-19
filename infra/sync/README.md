# OctoBot Sync Server — Infrastructure

Deploys the OctoBot sync server stack across multiple VPS nodes with zero-downtime rolling updates.

**Stack per node:** Garage (S3 storage) + OctoBot sync server + Nginx (reverse proxy with caching)

## Prerequisites

- Python 3.10+ with pip (`pip install -r infra/sync/requirements.txt` installs `ansible-core`)
- SSH access to target nodes (key-based, user `deploy` with sudo)
- OctoBot Docker image (`drakkarsoftware/octobot`) — the sync server runs via `OctoBot sync` CLI command (no separate image needed)

## Quick start

```bash
# 1. Install Ansible
pip install -r infra/sync/requirements.txt
cd infra/sync/ansible

# 2. Install Ansible Galaxy roles
ansible-galaxy install -r requirements.yml

# 3. Set up collections config
cp roles/stack/files/collections.json.example roles/stack/files/collections.json
vim roles/stack/files/collections.json        # adjust collections for your deployment

# 4. Set up credentials for your environment
cp vault.yml.example inventories/development/group_vars/all/vault.yml
cp hosts.yml.example inventories/development/hosts.yml

# 5. Set up SSH key
mkdir -p inventories/development/.ssh
cp ~/.ssh/id_rsa inventories/development/.ssh/id_rsa
chmod 600 inventories/development/.ssh/id_rsa

# 6. Fill in real values
vim inventories/development/hosts.yml                 # node IPs, zones, capacity
vim inventories/development/group_vars/all/vault.yml  # secrets

# 7. Encrypt sensitive files
ansible-vault encrypt inventories/development/group_vars/all/vault.yml
ansible-vault encrypt inventories/development/hosts.yml

# 8. Deploy
ansible-playbook playbooks/site.yml -i inventories/development
```

## Environments

| Environment | Branch/Trigger | Image Tag | Inventory |
|---|---|---|---|
| development | push to `dev` | `latest` | `inventories/development` |
| staging | push to `master` | `stable` | `inventories/staging` |
| production | git tag | version | `inventories/production` |

Deploy to a specific environment:

```bash
ansible-playbook playbooks/site.yml -i inventories/staging
ansible-playbook playbooks/site.yml -i inventories/production
```

Bare `ansible-playbook` without `-i` defaults to development (configured in `ansible.cfg`).

## Playbooks

| Playbook | Purpose | When to use |
|---|---|---|
| `site.yml` | Full stack rolling deploy | First deploy, infra changes, Garage config changes |
| `deploy-octobot-sync.yml` | App-only rolling update | New app version (fast — only restarts OctoBot Sync) |
| `setup-garage.yml` | Cluster bootstrap | Once after first `site.yml` — creates bucket + API key |

### First-time setup

```bash
# 1. Deploy the full stack (Garage + OctoBot Sync + Nginx)
ansible-playbook playbooks/site.yml -i inventories/production

# 2. Bootstrap the Garage cluster (connects nodes, assigns layout, creates bucket + key)
ansible-playbook playbooks/setup-garage.yml -i inventories/production

# 3. Save the S3 credentials output by step 2 into vault.yml
ansible-vault edit inventories/production/group_vars/all/vault.yml

# 4. Save the node IDs into hosts.yml (garage_node_id per host)
ansible-vault edit inventories/production/hosts.yml

# 5. Re-deploy with real S3 credentials
ansible-playbook playbooks/site.yml -i inventories/production
```

### Routine app deploy

```bash
ansible-playbook playbooks/deploy-octobot-sync.yml -i inventories/production
```

## Credentials

All secrets are managed via [Ansible Vault](https://docs.ansible.com/ansible/latest/vault_guide/).

### SSH keys per environment

Each environment has its own SSH key at `inventories/<env>/.ssh/id_rsa` (gitignored):

```bash
mkdir -p inventories/production/.ssh
ssh-keygen -t ed25519 -f inventories/production/.ssh/id_rsa -N ""
# Copy the public key to your nodes:
ssh-copy-id -i inventories/production/.ssh/id_rsa.pub deploy@node-ip
```

When deploying to a non-default environment, pass the key explicitly:

```bash
ansible-playbook playbooks/site.yml -i inventories/production \
  --private-key inventories/production/.ssh/id_rsa
```

### Encrypted files per environment

| File | Contents |
|---|---|
| `inventories/<env>/hosts.yml` | Node IPs, garage node IDs |
| `inventories/<env>/group_vars/all/vault.yml` | S3 keys, encryption secrets, Garage tokens |
| `inventories/<env>/.ssh/` | SSH private key for the `deploy` user (gitignored) |

### Editing encrypted files

```bash
# Edit in-place (opens $EDITOR)
ansible-vault edit inventories/production/group_vars/all/vault.yml

# Or decrypt to a gitignored temp file, edit, then re-encrypt
ansible-vault decrypt inventories/production/group_vars/all/vault.yml \
  --output inventories/production/group_vars/all/vault.dec.yml
vim inventories/production/group_vars/all/vault.dec.yml
ansible-vault encrypt inventories/production/group_vars/all/vault.dec.yml \
  --output inventories/production/group_vars/all/vault.yml
rm inventories/production/group_vars/all/vault.dec.yml

# Same for hosts
ansible-vault decrypt inventories/production/hosts.yml \
  --output inventories/production/hosts.dec.yml
vim inventories/production/hosts.dec.yml
ansible-vault encrypt inventories/production/hosts.dec.yml \
  --output inventories/production/hosts.yml
rm inventories/production/hosts.dec.yml

# Re-encrypt with a new password
ansible-vault rekey inventories/production/group_vars/all/vault.yml
```

### Pre-commit hook

Prevents accidentally committing unencrypted `vault.yml` or `hosts.yml`:

```bash
# Unix / macOS
cp infra/sync/ansible/scripts/pre-commit-vault-check.py .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Windows (Git Bash)
cp infra/sync/ansible/scripts/pre-commit-vault-check.py .git/hooks/pre-commit
```

### Vault password

The vault password is read from the `ANSIBLE_VAULT_PASSWORD` environment variable (via `scripts/vault-password.sh`). Set it before running playbooks:

```bash
export ANSIBLE_VAULT_PASSWORD="your-vault-password"
```

Or pass it interactively:

```bash
ansible-playbook playbooks/site.yml -i inventories/production --ask-vault-pass
```

### Generating secrets

```bash
# Garage RPC secret
openssl rand -hex 32

# Garage admin/metrics tokens
openssl rand -base64 32

# Encryption secrets
openssl rand -base64 48
```

### Required vault variables

See `vault.yml.example` for the full list:

| Variable | Purpose |
|---|---|
| `vault_garage_rpc_secret` | Shared secret for Garage inter-node RPC |
| `vault_garage_admin_token` | Garage admin API authentication |
| `vault_garage_metrics_token` | Garage metrics endpoint authentication |
| `vault_s3_access_key` | S3 API access key (from `setup-garage.yml`) |
| `vault_s3_secret_key` | S3 API secret key (from `setup-garage.yml`) |
| `vault_platform_pubkey_evm` | Platform EVM address (identity) |
| `vault_encryption_secret` | User data encryption key |
| `vault_platform_encryption_secret` | Platform data encryption key |

## Adding a new node

1. Edit the environment's `hosts.yml` — add a new entry under `sync_nodes`
2. Run `site.yml` with `--limit` to deploy only to the new node:
   ```bash
   ansible-playbook playbooks/site.yml -i inventories/production --limit new-node.example.com
   ```
3. Run `setup-garage.yml` to assign the new node in the Garage layout (bucket/key creation is skipped — they replicate automatically)

## Zero-downtime guarantee

- `serial: 1` — one node updated at a time
- Garage `replication_factor=3` — quorum needs 2/3, losing 1 is safe
- OctoBot sync is stateless — restart loses nothing
- Health checks must pass before moving to next node
- 10s pause between nodes for data re-sync

## CI/CD

Automated via GitHub Actions (`.github/workflows/main.yml`):

1. **`docker`** (existing) — builds the OctoBot image (`drakkarsoftware/octobot`), which includes the sync server
2. **`sync-deploy`** — after `docker` succeeds, runs Ansible `deploy-octobot-sync.yml` against the right environment

The sync server uses the same OctoBot image with `OctoBot sync` as the entry point — no separate build step needed.

Required GitHub secrets:

| Secret | Purpose |
|---|---|
| `SYNC_DEPLOY_SSH_KEY` | Ed25519 private key for the `deploy` user on VPS nodes |
| `SYNC_ANSIBLE_VAULT_PASSWORD` | Vault password for decrypting secrets |
| `SYNC_NODE_IPS` | Space-separated list of node IPs (for ssh-keyscan) |

## Nginx caching

Nginx config is auto-generated from `collections.json` (via `generate_nginx_conf.py`):

- **Public + pull_only** collections — cached 1h
- **Public + writable** collections — cached 30s
- **Private** collections — no cache, proxied directly
- `X-Cache-Status` header on cached routes for debugging
