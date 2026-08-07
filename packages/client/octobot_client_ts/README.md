# @drakkar.software/octobot-client

Talk to a self-hosted OctoBot node from TypeScript: wallet identity, accounts, automations,
strategies, and user actions over the Starfish sync transport.

## What this is not

- **No local state.** Every read is a fresh pull from the node; nothing is cached.
- **No persistence.** There is no store, no database, no `AsyncStorage`.
- **No offline queue.** If the node is unreachable, a call fails — it does not queue for later.
- **No CRDT merge.** This package has no concept of "local edits reconciled with remote state."
- **No React.** No hooks, no components, no dependency on any UI framework.

If you need any of the above (an offline-first mobile app syncing across devices, say), build that
layer on top of this package — see [Advanced: building an offline layer on top](https://docs.octobot.cloud/client-sdk/advanced-primitives)
for the subpath exports meant for exactly that.

## Install

```bash
npm install @drakkar.software/octobot-client
```

**Runtime requirements:** WebCrypto (`crypto.subtle` — SHA-256/512, HMAC, PBKDF2, AES-GCM, HKDF),
`fetch`, `btoa`/`atob`, `AbortController`. Available natively in Node ≥18, all modern browsers, and
Deno/Bun. React Native needs a crypto polyfill (`react-native-quick-crypto` or similar) — this
package does not bundle one.

## Hello world

```ts
import { connectOctoBot, strategy } from '@drakkar.software/octobot-client'

const octobot = await connectOctoBot({
  url: 'http://192.168.1.10:5001',
  seed: process.env.OCTOBOT_PRIVATE_KEY!, // a raw 0x-prefixed private key
})

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

## Five concepts

1. **A node is a server you point at.** `connectOctoBot({ url, seed })` — no registration, no
   cloud account. Anyone running their own OctoBot node can be your `url`.
2. **The wallet IS the identity.** There's no separate login. The private key (or a BIP39 mnemonic,
   which derives one) deterministically derives both the address the node authorizes and the
   encryption key for everything synced to it. See
   [Identity](https://docs.octobot.cloud/client-sdk/identity) — this is the single most important
   thing to get right, and the easiest to get subtly wrong.
3. **Collections, not tables.** `accounts`, `settings`, `strategies`, `user-data` are documents at
   fixed paths under `users/{identity}/...`, pulled and pushed as whole blobs, encrypted per-collection.
4. **User actions are a queue, not an RPC call.** Creating an account or starting an automation
   doesn't happen synchronously — it appends one element to an append-only queue the node consumes
   and executes. `ActionHandle.settled()` is how you wait for the result. See
   [User actions](https://docs.octobot.cloud/client-sdk/user-actions).
5. **`ActionHandle` work starts eagerly.** The moment `accounts.create()`/`automations.create()`
   returns a handle, the underlying action is already appended (and, for automations, the two-phase
   orchestration is already running). `settled()` just lets you observe the outcome — a caller who
   never awaits it still leaves nothing half-done.

## API map

| | |
|---|---|
| `connectOctoBot(options)` | Connect to a node. Returns an `OctoBotClient`. |
| `strategy.dca/grid/marketMaking/copy/signal/index/genericProcess(input)` | Pure, zero-I/O strategy builders. |
| `strategy.build(input)` / `.toInput(strategy)` / `.bumpVersion(v)` | The discriminated-union entry point, its inverse, and version bumping. |
| `client.accounts.list/get/create/update/delete/refresh/trading` | Exchange, wallet, and generic accounts. |
| `client.automations.list/get/create/update/stop` | Running bots. |
| `client.strategies.list/get/create/update/delete` | Reconstructed from the action history — the node has no strategies collection of its own. |
| `client.settings.get/patch/replace` | An opaque document the node stores encrypted and never reads. |
| `client.node.status/tradedPairs/predictedOrderBook/requiredFunds/dslKeywords/exportWallet/createGenericProcessBot` | The node's direct REST API. The last three need `basicAuth`. |
| `client.documents.pull/push/append` + `.raw` | Escape hatch: any collection, the raw `StarfishClient`. |
| `client.close()` | Drops the derived-key cache. |
| `createReadOnlyPairing(seed, derivation, node)` | Mint a scoped, node-enforced read-only credential for a less-trusted device. See [Read-only devices](https://docs.octobot.cloud/client-sdk/read-only-pairing). |
| `connectReadOnlyDevice(pairingPayload)` | Connect with that credential instead of a seed. Write methods return a `ProposedAction` (build, don't send) instead of an `ActionHandle`. |
| `startPairingRequest(options)` / `fetchPairingRequestByCode({code, rendezvous})` | Website side: publish a device-code pairing request; phone side: look it up (returns `{request, hash}`). See [Website pairing](https://docs.octobot.cloud/client-sdk/website-pairing). |
| `mintPairingGrant(session, request)` / `publishPairingGrant(...)` | Phone side, on approval: invite the website's device into the cloud mirror as a read-only `space:member`, then seal and publish the grant. |
| `awaitPairingGrant(session, options)` / `fetchPairingGrant(session, options)` | Website side: wait for (or poll for) the grant, unseal it, and live-read the mirror collections it covers. |
| `revokePairingGrant(...)` / `clearPairingGrant(...)` | Unpair: remove the website's space membership and clear the rendezvous slot. |

## Errors

Every `OctoBotClient`/`ReadOnlyOctoBotClient` method, and the `client/pairing/*` functions above
(`startPairingRequest`, `fetchPairingGrant`, etc.), throw an `OctoBotError` subclass (or let an
`AbortError` `DOMException` through unwrapped, per the platform convention). Switch on `.code`
rather than `instanceof` if you need the check to survive a duplicated package instance. Full
taxonomy, extra fields, and handling patterns: [Errors](https://docs.octobot.cloud/client-sdk/errors).
The two exceptions are the I/O-free `identity/pairingRequest.js` and `identity/pairing.js` pure
functions (`createPairingRequest`, `parsePairingRequest`, `createReadOnlyPairing`,
`parseReadOnlyPairing`) — they validate/build payloads only, never touch the network, and throw a
plain `Error` rather than an `OctoBotError`.

| Class | `code` | When |
|---|---|---|
| `OctoBotConfigError` | `'config'` | Bad `ConnectOptions` — unparseable `url`, or a `node.*` call made without `basicAuth`. |
| `OctoBotConnectionError` | `'unreachable' \| 'timeout' \| 'aborted'` | The node could not be reached. |
| `OctoBotAuthError` | `'unauthorized'` | The node answered but didn't authorize this wallet — carries `.address`/`.userId`/`.derivation` so you can see what was tried. |
| `OctoBotHttpError` | `'http'` | A node REST call answered non-2xx. Carries `.status`. |
| `OctoBotConflictError` | `'conflict'` | A document push raced another writer. Carries `.serverHash` — pull again and retry. |
| `OctoBotActionError` | `'action_failed'` | The node executed a queued action and rejected it. Not retriable by resubmitting unchanged. |
| `OctoBotTimeoutError` | `'action_timeout'` | `settled()` gave up waiting — the action may still complete. |
| `OctoBotScopeError` | `'forbidden_collection'` | A read-only session reached a collection outside its pairing grant — thrown client-side, before any request. |

## Escape hatches

- **Custom `fetch`** — `ConnectOptions.fetch`, for proxies, mTLS, or a React Native polyfill.
- **`verify: false`** — skip the connect-time probe; `connectOctoBot()` does zero I/O and the first
  real call surfaces any problem.
- **Raw documents** — `client.documents.pull/push/append` for any collection, typed loosely; and
  `client.documents.raw` for the underlying `StarfishClient` and cap provider directly.
- **`seedDerivation: 'auto'`** — tries every registered derivation scheme and keeps whichever the
  node authorizes.

Full detail: [Escape hatches](https://docs.octobot.cloud/client-sdk/escape-hatches).

## Compatibility

| This package | `@drakkar.software/octobot-protocol` | Minimum node |
|---|---|---|
| `0.3.0` | `^0.6.0` | protocol 0.4.0 |

## More

- [Client SDK docs](https://docs.octobot.cloud/client-sdk/getting-started) — one topic per page,
  start with Getting Started.
- [`CHANGELOG.md`](CHANGELOG.md)
- [Wire contract](https://docs.octobot.cloud/client-sdk/wire-contract) — every literal string shared
  with the node's Python implementation, for anyone changing either side.
