---
title: "Read-Only Devices"
description: "Pair a less-trusted client as a read-only companion: a real, node-enforced scoped credential, plus offline action proposals for a privileged device to review and execute."
sidebar_position: 8
mdx:
  format: mdx
---

import DemoEmbed from '@site/src/components/demo/Embed';

# Read-only devices

A less-trusted client — a CLI, an AI agent, a second phone, anything embedding this package without
holding the real wallet seed — can act as a **read-only companion** to a node. It can read accounts
and automations, but any write attempt builds the action and hands you back a **proposal** instead of
sending it: a QR-encodable payload for a privileged device (one that actually holds the seed) to scan,
review, and execute.

This page covers the case where the **privileged device initiates** — it mints a credential and shows
a QR for the other device to scan. If your less-trusted client is a **website**, it can't scan a QR the
phone displays; see [Website pairing](website-pairing.md) for the reverse flow, which uses a short
device code instead of a QR and delivers a sealed data snapshot rather than a node credential.

<DemoEmbed section="propose" />

## The loop

1. The privileged device (the one with the seed) calls `createReadOnlyPairing()` and shows the
   resulting payload as a QR code.
2. The other client scans it and calls `connectReadOnlyDevice()` — no seed anywhere on this path.
3. That client reads normally (`accounts.list()`, `automations.list()`, ...) and, on any write call,
   gets a `ProposedAction` back instead of an `ActionHandle` — it shows that as a QR code too.
4. The privileged device scans the proposal, reviews it, and executes it with its own real client.

## Minting a pairing

```ts
import { createReadOnlyPairing } from '@drakkar.software/octobot-client/identity'

const { payload } = await createReadOnlyPairing(seed, 'bip44', { host: '192.168.1.10', port: 5001 })
// render `payload` as a QR code with whatever QR library you already have —
// this package never renders one itself, it only returns the string to encode.
```

The payload is fully self-contained (it carries the node's endpoint), so the scanning side needs
nothing else to connect.

**Default scope**: `ops: ['read', 'list']` — never `'write'` — restricted to the `userData` and
`accounts` collections. That's enough to reconstruct `accounts.list()`, `automations.list()`, *and*
`strategies.list()` (the last one is implemented via a `userData` pull, not the legacy `strategies`
collection), with no access to `settings` or `accountTrading`. Override with the `collections` option
if you need a different subset — `ops` is always exactly `['read', 'list']`, this function has no
option to widen it.

**The cap's `ops` restriction is not yet node-enforced — this is a client-side guarantee today, stated
plainly rather than overclaimed.** The pairing mints an ephemeral Ed25519+X25519 keypair (the scanning
device's own, generated fresh — never the wallet's root key) and a cap-cert the wallet's root key signs
for it, restricted to `ops: ['read', 'list']`. But an OctoBot node currently authorizes every collection
by identity alone (`readRoles=["self"], writeRoles=["self"]`), not by the cap's `ops`/`collections`
scope — so a device holding this payload's *cap* is not, today, physically prevented by the node from
writing. What this package guarantees instead: `connectReadOnlyDevice()`'s `accounts`/`automations`/
`strategies` write methods never call the node's append endpoint on this session's behalf — they always
build a `ProposedAction` and return it. See `OctoBotScopeError` for the related collection-level gate
this package does enforce (below).

**What actually decides what a read-only device can decrypt**: each granted collection gets its own
derived AES-256 key (`collectionKeys`, one entry per collection in `scope.collections`), computed as
`HKDF-SHA256(the wallet's derived encryption secret, salt, collection-specific info)`. That derivation
is one-way and collection-independent — holding the `userData` key reveals nothing about the `accounts`
key, and neither reveals the wallet's secret, let alone its private key. `connectReadOnlyDevice()`
throws `OctoBotScopeError` for any collection outside the grant, client-side, before any network
request — so even though the node doesn't yet enforce scope, this package never even tries to reach for
key material it wasn't given. A device holding this payload can decrypt exactly the granted collections
and can never mint a broader grant (it never touches the root private key). Don't pair a device you
don't trust to read your data, and treat the collections you grant as the real security boundary today
— not the cap's `ops` field.

## Connecting read-only

```ts
import { connectReadOnlyDevice } from '@drakkar.software/octobot-client'

const octobot = await connectReadOnlyDevice(pairingPayload)
const accounts = await octobot.accounts.list()               // works, real pull
const proposed = await octobot.automations.stop(automationId) // builds, does not send
console.log(proposed.payload)                                 // render this as a QR
```

`ReadOnlyOctoBotClient` has the same method names as the full `OctoBotClient` — `accounts.create/
update/delete/refresh`, `automations.create/update/stop`, `strategies.create/update/delete` — so
nothing renames when a caller migrates between the two. The difference is only in what each write
method returns: a `ProposedAction` (`{ actions, payload }`) instead of an `ActionHandle`.

`automations.create()`'s proposal carries **two** actions, `strategy_create` then `automation_create`,
the second tagged `after: 'previous-confirmed'` — the same node-side race `connectOctoBot()`'s facade
sequences around (see [Automations](automations.md)) applies here too. This read-only session has no
append rights to sequence it itself; the executing side must honor that ordering when it processes the
proposal.

## Executing a proposal

```ts
import { decodeActionProposal } from '@drakkar.software/octobot-client/protocol'

const proposal = decodeActionProposal(scannedPayload)
// proposal.label — a human-readable summary for a confirm screen
// proposal.actions — [{ configuration, after? }], in append order
```

This package's facade doesn't ship an "execute a proposal" method — appending is exactly what
`connectOctoBot()`'s own `accounts`/`automations`/`strategies` methods already do. Walk
`proposal.actions` in order using your own `OctoBotClient`'s underlying append mechanism (or the
`protocol/actions.js` builders directly, via the lower-level primitives — see
[Advanced primitives](advanced-primitives.md)), honoring `after: 'previous-confirmed'` by polling the
prior action to completion (the same pattern `runCreateAutomation` uses internally) before appending
the next one.
