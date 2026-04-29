---
title: Sync
description: Cryptographically authenticated sync server and client for multi-instance OctoBot data sharing, built on FastAPI and the Starfish framework.
sidebar_position: 1
---

# Sync

`octobot_sync` is the synchronization server and client for OctoBot. It lets multiple OctoBot instances share collections of data — bot configs, accounts, signals, product metadata — over HTTPS, with every request authenticated by an EVM wallet signature and every stored payload encrypted at rest.

## Architecture

The package is built on top of [Starfish](https://github.com/Drakkar-Software/starfish-server), which provides the generic collection routing, role-based access control, encryption, and replica sync machinery. `octobot_sync` contributes the OctoBot-specific layer: the EVM-based auth scheme, the chain registry for on-chain ownership resolution, the collection definitions, and the application entry points. This split means the sync server's core machinery is not OctoBot-specific and can be reused elsewhere, while the collections and auth rules live where they can evolve with the product.

A sync deployment can run in two modes. A **primary server** is backed by S3-compatible object storage and is the canonical source of truth. A **replica server** is backed by local filesystem storage and mirrors a subset of the primary's collections using Starfish's `ReplicaManager`. The client entry point `create_sync_client` handles both: it returns a connected client and can optionally spin up a local replica server in a daemon thread before connecting to it, so an OctoBot instance can work against a nearby local copy.

## Authentication

Every request carries five HTTP headers: the caller's EVM address, an EIP-191 personal-sign signature, a millisecond Unix timestamp, a UUID nonce, and the chain ID in `evm:<chainId>` format. The server builds a canonical string from the method, path, timestamp, nonce, and SHA-256 of the request body, then verifies the signature against that string. Timestamps are checked within ±10 seconds of server time, and nonces are tracked for 30 seconds to prevent replay attacks. A caller whose address matches `PLATFORM_PUBKEY_EVM` receives admin role; all other valid callers receive user role.

When a request carries a `productId` path parameter, a role enricher runs and queries registered chains for on-chain ownership and access rights. Owning a product grants owner and member roles; having access grants member only. These roles are what determine which collections the caller can read or write, making access control data-driven rather than hard-coded.

## Collections

A collection is the unit of storage. Each one defines a storage path template, read/write role requirements, encryption mode, and optional constraints on size, schema, MIME type, and rate limiting. The path template (for example `users/{identity}` or `items/{itemId}/feed/{version}`) serves double duty: it determines where data is stored and whether the collection is replicable. Template variables make a collection non-replicable, because there is no single canonical path the replica can pull from.

When no `collections.json` is present the package falls back to a default config covering bots, accounts, and errors collections with appropriate role and encryption settings.

## On-chain layer

The chain layer provides an abstract interface for multi-chain support and an EVM implementation targeting Base. On-chain calls are TTL-cached to avoid hammering the RPC endpoint: ownership is cached for a year since it is treated as immutable, access rights for 60 seconds, and item lookups for 30 seconds. The cache tiers reflect how frequently each piece of data changes in practice.

## Replica sync

Only collections whose storage path contains no template variables can be replicated, since replication requires a single canonical pull path. Each replicable collection gets pull and push paths injected along with sync triggers — on-pull and scheduled — so the replica stays current both reactively and on a timer. Outgoing requests from the replica to the primary are authenticated using the same EVM signature scheme via `StarfishAuthProvider`.

## nginx integration

The package can generate an nginx reverse-proxy configuration from a `collections.json`. Public pull-only collections get a one-hour proxy cache; public writable collections get a 30-second cache; all other collections are proxied directly without caching. Collections with rate limiting enabled get a strict rate limit zone on push paths. This keeps the nginx configuration in sync with collection semantics automatically, rather than requiring manual alignment between the two.
