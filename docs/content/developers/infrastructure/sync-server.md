---
title: Sync Server
description: Deploying and operating the OctoBot sync server — primary and replica modes, authentication, nginx integration, and configuration.
sidebar_position: 1
---

# Sync Server

This page covers how to deploy and operate the sync server. For the package architecture — collections, authentication scheme, on-chain layer, and replica sync machinery — see the [Sync package overview](../packages/sync.md).

## Primary server

The primary server is the canonical source of truth. It uses S3-compatible object storage and is intended to run behind an nginx reverse proxy.

At startup the server needs S3 credentials (`S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_ENDPOINT`, `S3_BUCKET`, `S3_REGION`), a `PLATFORM_PUBKEY_EVM` address that determines which caller receives admin role, and two encryption secrets — `ENCRYPTION_SECRET` for per-identity data and `PLATFORM_ENCRYPTION_SECRET` for platform-level data. Both secrets are HKDF roots; losing either makes previously stored encrypted data unrecoverable, so they should live in a secrets manager or vault from the start.

On-chain access resolution uses the Base chain by default with a public RPC. For production, set `EVM_BASE_RPC` to a dedicated endpoint and `EVM_CONTRACT_BASE` to the access-control contract address to avoid rate limiting.

The server binds to `0.0.0.0` on the port from `PORT` (default `3000`). The `/health` endpoint requires no authentication and is suitable for load balancer checks.

## Replica server

A replica is a local mirror backed by the filesystem instead of S3. It connects to a primary, pulls replicable collections on startup and on a timer, and serves reads from local storage. This is useful for edge deployments or any OctoBot instance that needs low-latency reads without hitting the primary on every request.

The replica authenticates to the primary using an EVM private key. The corresponding address must have at least user-level access to the collections being replicated. Write mode can be `bidirectional` (replica pushes local writes back) or `pull_only` (read-only mirror). The sync interval defaults to 60 seconds.

Only collections with a fixed storage path can be replicated — templated paths like `users/{identity}` have no single canonical URL to pull from, so they are served locally only. The default collection set is all templated, which means a default replica acts as a local write cache without pulling anything from the primary. Data lands in `~/.octobot/sync_data` unless overridden.

## Client connection

OctoBot instances connect via `create_sync_client`, which returns a client pointed at the sync URL. When `start_replica_server=True`, it spins up a local replica in a daemon thread and connects to it instead — the caller doesn't need to know whether it's talking to a primary or a replica. The replica thread is a module-level singleton, so repeated calls reuse the same server.

## nginx integration

The sync server ships an nginx config generator that reads `collections.json` and produces a server block with caching and rate-limiting rules matched to the collection definitions. This keeps the two in sync automatically rather than requiring manual alignment.

```bash
python -m octobot_sync.util.nginx_conf collections.json > /etc/nginx/conf.d/sync.conf
```

Three caching tiers are applied: public pull-only collections get a one-hour cache, public writable collections get thirty seconds, and everything else is proxied directly. Collections with rate limiting enabled get a strict zone on their push paths. Routes outside `/v1/` and `/health` return 404 at the nginx level, so the application never receives unexpected requests.
