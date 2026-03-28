---
title: Overview
description: Introduction to OctoBot Node — a distributed automation execution platform with standalone and replica deployment modes.
sidebar_position: 1
---

# Node

OctoBot Node is a distributed automation execution platform that runs trading automations at scale. It exposes a FastAPI-based REST API, a DBOS-powered task scheduler, and a React web dashboard. Nodes can run independently or coordinate through a master–consumer topology backed by PostgreSQL.

## Standalone mode

The simplest deployment is a single node with no external database. The scheduler stores its state in a local SQLite file, and the node handles both scheduling and execution. This is suitable for single-machine setups where coordination between nodes is not needed.

Each standalone node is fully independent — there is no awareness of other nodes and no shared state.

## Replica mode

Replica mode introduces a master–consumer topology for distributing work across machines. Exactly one node acts as the master: it runs PostgreSQL, schedules tasks, and assigns them to consumers. Consumer nodes connect to the master's database and pull work from the shared queue.

The Ansible inventory enforces the single-master constraint at deploy time. Consumer nodes are configured with the master's database URL automatically based on the inventory topology. The master listens on PostgreSQL's default port, and firewall rules are opened from each consumer to the master when replica mode is active.

Write traffic flows through the master's scheduler. Consumers execute workflows and report results back through the shared PostgreSQL backend. A pause is inserted between node deployments during rolling updates to avoid disrupting in-flight work.

## Docker Compose stack

Each node runs as a Docker Compose stack. The core service is the OctoBot container, which runs the FastAPI server on port 8000 and the web UI on port 5001.

Optional sidecar services extend the stack. Nginx provides TLS termination and rate limiting when enabled. Tor provides a SOCKS5 proxy that routes exchange traffic through the Tor network for anonymization. In replica mode, the master node additionally runs a PostgreSQL container for the shared scheduler backend.

Persistent data lives in named volumes: user configuration and state, tentacle plugins, application logs, and database storage (master only).

## Health checks

The stack includes health checks for each service. The OctoBot API is checked via the OpenAPI endpoint, the web UI via its port, PostgreSQL via `pg_isready` (replica mode only), and nginx via a dedicated `/health` route. These endpoints are suitable for load balancer probes and monitoring.

## Next steps

- [Configuration](./configuration.md) — feature flags, secrets, resource limits, and tentacle installation
- [Deployment](./deployment.md) — Ansible setup, inventory topology, and playbooks
- [Security](./security.md) — OS hardening, TLS, container isolation, and nginx protections
