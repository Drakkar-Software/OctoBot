---
title: "Getting Started"
description: "Install @drakkar.software/octobot-client, connect to a self-hosted OctoBot node with a wallet private key, and the five things worth knowing before you build anything."
sidebar_position: 1
mdx:
  format: mdx
---

import DemoEmbed from '@site/src/components/demo/Embed';

# Getting started

A TypeScript client for a self-hosted OctoBot trading node: wallet identity, accounts, automations,
strategies, and an append-only action queue, over the Starfish sync transport. No cloud account, no
registration — anyone running their own node can be your `url`.

<DemoEmbed section="overview" />

## What this is not

- **No local state.** Every read is a fresh pull from the node; nothing is cached.
- **No persistence.** There is no store, no database, no `AsyncStorage`.
- **No offline queue.** If the node is unreachable, a call fails — it does not queue for later.
- **No CRDT merge.** This package has no concept of "local edits reconciled with remote state."
- **No React.** No hooks, no components, no dependency on any UI framework.

If you need any of the above (an offline-first mobile app syncing across devices, say), build that
layer on top of this package — see [Advanced primitives](advanced-primitives.md) for the subpath
exports meant for exactly that.

## Install

```bash
npm install @drakkar.software/octobot-client
```

**Runtime requirements:** WebCrypto (`crypto.subtle` — SHA-256/512, HMAC, PBKDF2, AES-GCM, HKDF),
`fetch`, `btoa`/`atob`, `AbortController`. Available natively in Node ≥18, all modern browsers, and
Deno/Bun. React Native needs a crypto polyfill (`react-native-quick-crypto` or similar) — this
package does not bundle one.

**License: LGPL-3.0** — worth knowing before week three, not after.

## Find your node's address

An OctoBot node listens on `http://<host>:5001` by default (`5001` is the default REST/sync port).
On the same LAN as your node, this is usually the machine's local IP: `http://192.168.1.10:5001`.

## Get a private key

A raw `0x`-prefixed secp256k1 private key is the primary way to authenticate — pass it as-is, no
derivation needed. A BIP39 mnemonic also works (`connectOctoBot`'s `seed` option accepts either),
deterministically deriving a private key via real BIP44 — see [Identity](identity.md) for that path.
Either way, don't paste a real wallet's key/phrase into example code; generate a fresh throwaway one
while you're getting the connection working.

## The five things to know before you build anything

1. **A node is a server you point at.** `connectOctoBot({ url, seed })` — no registration, no
   cloud account. Anyone running their own OctoBot node can be your `url`.
2. **The wallet IS the identity.** There's no separate login. The private key (or a BIP39 mnemonic,
   which derives one) deterministically derives both the address the node authorizes and the
   encryption key for everything synced to it. See [Identity](identity.md) — this is the single most
   important thing to get right, and the easiest to get subtly wrong.
3. **Collections, not tables.** `accounts`, `settings`, `strategies`, `user-data` are documents at
   fixed paths under `users/{identity}/...`, pulled and pushed as whole blobs, encrypted
   per-collection. See [Collections and encryption](collections-and-encryption.md).
4. **User actions are a queue, not an RPC call.** Creating an account or starting an automation
   doesn't happen synchronously — it appends one element to an append-only queue the node consumes
   and executes. See [User actions](user-actions.md) — this is the thing most likely to make your
   first integration behave unexpectedly if you skip it.
5. **`ActionHandle` work starts eagerly.** The moment `accounts.create()`/`automations.create()`
   returns a handle, the underlying action is already appended (and, for automations, the two-phase
   orchestration is already running). `settled()` just lets you observe the outcome — a caller who
   never awaits it still leaves nothing half-done.

## Connect, and make your first calls

```ts
import { connectOctoBot, strategy } from '@drakkar.software/octobot-client'

const octobot = await connectOctoBot({
  url: 'http://192.168.1.10:5001',
  seed: process.env.OCTOBOT_PRIVATE_KEY!, // a raw 0x-prefixed private key
})

console.log(octobot.address) // the EIP-55 checksummed address the node authorized

const [account] = await octobot.accounts.list()

const dca = strategy.dca({ pairs: ['BTC/USDT'], buyOrderAmount: '25' })
const action = await octobot.automations.create({
  name: 'My DCA',
  strategy: dca,
  accountIds: [account.id],
})

const automation = await action.settled() // polls the node until it confirms
console.log(automation.id, automation.status) // 'live'
```

By default, `connectOctoBot` probes the node and verifies the wallet is authorized before resolving
— if it isn't, you get an `OctoBotAuthError` immediately, with a clear message about which
derivation was tried. Pass `verify: false` to skip this and do the check lazily on the first real
call instead — see [Escape hatches](escape-hatches.md).

## Next

- [Identity](identity.md) — the wallet/derivation model, and the #1 way to get stuck.
- [User actions](user-actions.md) — what `ActionHandle` is actually doing, and why `create()`
  resolving is not the same thing as "created."
- [Errors](errors.md) — every way a call can fail, and how to branch on it.
- [Read-only devices](read-only-pairing.md) — pair a less-trusted client with a scoped, node-enforced
  credential, and let it propose writes for a privileged device to review.
- [Live demo](/demo) — every panel on this and the following pages, in one place.
