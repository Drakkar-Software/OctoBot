---
title: Infrastructure Overview
description: Deployment infrastructure for OctoBot — sync servers, node scheduling, and supporting services.
sidebar_position: 1
---

# Infrastructure

This section covers the deployment and operational aspects of OctoBot's server-side components. For package architecture and code-level documentation, see [Packages](../packages/overview.md).

OctoBot can run as a standalone bot on a single machine, but several components support distributed and managed deployments:

- **[Sync Server](./sync-server.md)** — a cryptographically authenticated HTTPS service that lets multiple OctoBot instances share configurations, accounts, and signals. Runs in primary (S3-backed) or replica (local filesystem) mode. Authentication uses EVM wallet signatures with on-chain access resolution.

- **[Node](./node/overview.md)** — a distributed automation execution platform that runs trading automations at scale. Deploys as a Docker Compose stack with optional nginx, Tor, and PostgreSQL sidecars. Supports standalone single-node operation or a master–consumer topology for distributing work across machines.

