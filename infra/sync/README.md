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

# 3. Set up credentials for your environment
cp vault.yml.example inventories/development/group_vars/all/vault.yml
cp hosts.yml.example inventories/development/hosts.yml

# 4. Set up SSH key
mkdir -p inventories/development/.ssh
cp ~/.ssh/id_ed25519 inventories/development/.ssh/id_ed25519
chmod 600 inventories/development/.ssh/id_ed25519

# 5. Fill in real values
vim inventories/development/hosts.yml                 # node IPs, zones, capacity
vim inventories/development/group_vars/all/vault.yml  # secrets

# 6. Encrypt sensitive files
ansible-vault encrypt inventories/development/group_vars/all/vault.yml
ansible-vault encrypt inventories/development/hosts.yml

# 7. Deploy
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

Each environment has its own SSH key at `inventories/<env>/.ssh/id_ed25519` (gitignored):

```bash
mkdir -p inventories/production/.ssh
ssh-keygen -t ed25519 -f inventories/production/.ssh/id_ed25519 -N ""
# Copy the public key to your nodes:
ssh-copy-id -i inventories/production/.ssh/id_ed25519.pub deploy@node-ip
```

When deploying to a non-default environment, pass the key explicitly:

```bash
ansible-playbook playbooks/site.yml -i inventories/production \
  --private-key inventories/production/.ssh/id_ed25519
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

### Regenerating S3 keys

The S3 secret key is only returned by Garage at creation time. If it was lost, delete the key and recreate it:

```bash
# 1. SSH into any cluster node
ssh deploy@<node>

# 2. Read the admin token from the deployed Garage config
GARAGE_TOKEN=$(grep admin_token /opt/octobot-sync/garage.toml | awk -F'"' '{print $2}')

# 3. Get the key ID
KEY_ID=$(curl -s -H "Authorization: Bearer $GARAGE_TOKEN" \
  'http://127.0.0.1:3903/v2/GetKeyInfo?search=octobot-sync-key' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['accessKeyId'])")

echo "Key ID: $KEY_ID"

# 4. Delete the key
curl -s -X POST -H "Authorization: Bearer $GARAGE_TOKEN" \
  "http://127.0.0.1:3903/v2/DeleteKey?id=$KEY_ID"
```

Then re-run `setup-garage.yml` — it will create a new key and display the credentials:

```bash
ansible-playbook playbooks/setup-garage.yml -i inventories/<env>
```

Save the new credentials into vault.yml:

```bash
ansible-vault edit inventories/<env>/group_vars/all/vault.yml
# Update vault_s3_access_key and vault_s3_secret_key
```

Re-deploy to apply the new credentials:

```bash
ansible-playbook playbooks/site.yml -i inventories/<env>
```

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
| `ANSIBLE_SSH_KEY` | Ed25519 private key for the `deploy` user on VPS nodes |
| `ANSIBLE_VAULT_PASSWORD` | Vault password for decrypting secrets |

### Generating the CI/CD SSH key

Generate a dedicated ed25519 key pair (no passphrase — Actions reads it directly):

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f /tmp/deploy_ed25519 -N ""
```

Add the **private key** as the `ANSIBLE_SSH_KEY` GitHub secret (the exact contents of `/tmp/deploy_ed25519`).

On each VPS node, append the **public key** to `~/.ssh/authorized_keys` with forwarding disabled.

```bash
export NODE_IP=<ip> SSH_USER=<user>
echo "no-port-forwarding,no-X11-forwarding,no-agent-forwarding $(cat /tmp/deploy_ed25519.pub)" | ssh -i ~/.ssh/ed25519 $SSH_USER@$NODE_IP "tee -a ~/.ssh/authorized_keys"
```

### GitHub Environment protection

Store `ANSIBLE_SSH_KEY` and `ANSIBLE_VAULT_PASSWORD` inside a **GitHub Environment** (e.g., `production`) rather than as plain repository secrets. Configure the environment with:

- **Required reviewers** — at least one approver before a deployment can proceed
- **Branch restrictions** — only allow deployments from `master` (or your release branch)

This ensures the key is never exposed to workflows triggered by pull requests from forks or arbitrary branches.

## Admin: Fetching a specific file from S3 (local access)

`/garage` (inside the container) is the cluster management tool — it has no S3 file download command. Use `awscli` from the host pointed at the Garage S3 API on `localhost:3900`, with credentials from the vault.

```bash
# Install awscli
pip install awscli

# Configure Garage credentials (values from vault.yml)
aws configure set aws_access_key_id "<vault_s3_access_key>"
aws configure set aws_secret_access_key "<vault_s3_secret_key>"
aws configure set default.region garage

# List buckets
aws s3 ls --endpoint-url http://localhost:3900

# List objects under a prefix (to find the exact key path)
aws s3 ls "s3://<bucket>/<optional/prefix>" --endpoint-url http://localhost:3900

# Download a specific object
aws s3 cp "s3://<bucket>/<path/to/object>" /tmp/fetched_file --endpoint-url http://localhost:3900
```

> **Tip:** Port 3900 is the Garage S3 API — it listens only on localhost and is not exposed publicly. S3 credentials (`vault_s3_access_key` / `vault_s3_secret_key`) come from the Ansible vault.

## Nginx caching

Nginx config is auto-generated from `collections.json` (via `generate_nginx_conf.py`):

- **Public + pull_only** collections — cached 1h
- **Public + writable** collections — cached 30s
- **Private** collections — no cache, proxied directly
- `X-Cache-Status` header on cached routes for debugging
