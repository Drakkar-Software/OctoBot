---
title: Deployment
description: Setting up Ansible and deploying OctoBot Node — prerequisites, inventory configuration, playbooks, and rolling updates.
sidebar_position: 3
---

# Deployment

OctoBot Node is deployed using Ansible. Two playbooks handle different scenarios: a full-stack playbook for initial setup and infrastructure changes, and a fast-deploy playbook for application-only updates.

## Prerequisites

Install Ansible and the required external roles and collections.

```bash
pip install -r infra/node/requirements.txt

cd infra/node/ansible
ansible-galaxy install -r requirements.yml
ansible-galaxy collection install -r requirements.yml
```

This pulls in `geerlingguy.docker` for Docker installation, `geerlingguy.firewall` for iptables management, and `devsec.hardening` for OS and SSH hardening.

## Inventory

The inventory defines which machines to deploy to and how they relate to each other. Start from the example and adapt it.

```bash
cp inventories/hosts.yml.example inventories/hosts.yml
```

### Standalone topology

For independent nodes that don't coordinate, list hosts directly under `octobot_nodes`. Each runs its own SQLite-backed scheduler.

```yaml
all:
  children:
    octobot_nodes:
      hosts:
        my-node.example.com:
          ansible_host: 203.0.113.10
          ansible_user: deploy
```

### Replica topology

For a master–consumer setup, split hosts into `master_nodes` and `consumer_nodes` under `octobot_nodes`. The master runs PostgreSQL and schedules work; consumers pull tasks from the master's database.

```yaml
all:
  children:
    octobot_nodes:
      children:
        master_nodes:
          hosts:
            node-master.example.com:
              ansible_host: 203.0.113.10
              ansible_user: deploy
        consumer_nodes:
          hosts:
            node-consumer-1.example.com:
              ansible_host: 203.0.113.11
              ansible_user: deploy
            node-consumer-2.example.com:
              ansible_host: 203.0.113.12
              ansible_user: deploy
```

Several variables are computed automatically from group membership: which node is master, which is consumer-only, and where PostgreSQL listens. You don't need to set these manually.

Both playbooks validate the topology before executing. They enforce that at most one master exists, that consumers require `enable_replica_mode`, and that a master with replica mode has at least one consumer. Violations fail the playbook immediately.

## Configuration

Edit `inventories/group_vars/all/vars.yml` to set feature flags and secrets. See [Configuration](./configuration.md) for all available options.

```yaml
# inventories/group_vars/all/vars.yml
enable_nginx: true
expose_web_ui: true
enable_hardening: true

secret_key: "your-jwt-secret"
admin_username: "admin@yourdomain.com"
admin_password: "strong-password"
```

For replica mode, also set the PostgreSQL password:

```yaml
enable_replica_mode: true
postgres_password: "db-password"
```

Alternatively, pass secrets on the command line to avoid storing them in files:

```bash
ansible-playbook playbooks/site.yml \
  --extra-vars "secret_key=mysecret admin_password=mypass" \
  --private-key ~/.ssh/id_ed25519
```

## Full-stack deploy

The `site.yml` playbook provisions the entire environment from scratch: system packages, Docker, firewall rules, user accounts, Compose files, nginx configuration, TLS certificates, and the application containers.

```bash
ansible-playbook playbooks/site.yml --private-key ~/.ssh/id_ed25519
```

It uses a rolling strategy — one node at a time (`serial: 1`) with a ten-second pause between nodes. In replica mode, master nodes deploy before consumers, ensuring PostgreSQL is available before any consumer tries to connect. Consumer nodes verify they can reach the master's PostgreSQL port before starting OctoBot.

After bringing up the stack, the playbook runs health checks against each service. OctoBot's API endpoint, the web UI (if exposed), PostgreSQL (if master), and nginx (if enabled) must all pass before the node is considered healthy and the playbook moves to the next one.

Use this playbook for initial deployments, configuration changes, infrastructure updates, or when you need to re-provision the full stack.

### Limiting to specific hosts

```bash
# Deploy only the master
ansible-playbook playbooks/site.yml --limit node-master.example.com --private-key ~/.ssh/id_ed25519

# Dry run to preview changes
ansible-playbook playbooks/site.yml --check --diff --private-key ~/.ssh/id_ed25519
```

## Fast app-only deploy

The `deploy-octobot-node.yml` playbook skips infrastructure provisioning. It pulls the latest Docker image and recreates only the OctoBot container, leaving nginx, Tor, and PostgreSQL untouched.

```bash
ansible-playbook playbooks/deploy-octobot-node.yml --private-key ~/.ssh/id_ed25519
```

This is the typical post-CI workflow: a new image is pushed to the registry, then this playbook rolls it out across all nodes. It uses the same rolling strategy and health checks as the full-stack playbook.

## What each role does

The full-stack playbook chains several roles in order.

`geerlingguy.firewall` configures iptables rules. By default, ports 22, 80, and 443 are open. Additional rules can be added via `firewall_additional_rules` in group vars — for example, opening port 5432 from specific consumer IPs in replica mode.

`geerlingguy.docker` installs Docker CE with the Compose plugin and adds the `deploy` user to the Docker group.

`common` creates the `deploy` system user, verifies Docker's iptables chains are intact (restarting Docker if needed), and creates the deployment directory at `/opt/octobot-node`.

`octobot` renders the Docker Compose file, `.env` file, and nginx configuration from templates, generates a self-signed TLS certificate for the host, pulls images, starts the stack, installs custom tentacles if configured, and runs health checks.

In replica mode, consumer nodes additionally run the `postgres` role, which waits up to 60 seconds for the master's PostgreSQL port to be reachable before proceeding. If the master is unreachable, the consumer deployment fails rather than starting OctoBot with a broken database connection.
