---
title: "Website Pairing"
description: "Let a third-party website pair read-only with a user's OctoBot without scanning a site-rendered QR: a short device code, approved on the phone, mints a live read-only grant against the user's cloud mirror."
sidebar_position: 9
mdx:
  format: mdx
---

import DemoEmbed from '@site/src/components/demo/Embed';

# Website pairing

[Read-only devices](read-only-pairing.md) covers the case where the privileged device (the one with
the seed) initiates: it shows a QR, a less-trusted device scans it. This page covers the reverse — a
**website** is the less-trusted party, and it cannot scan a QR the phone displays. The website has to
initiate instead, and the phone approves.

<DemoEmbed section="website-pairing" />

**Why this can't just be the same QR flow with the roles swapped.** If the website rendered a QR and
the phone scanned it, there would be no channel binding that scan to the browser session that rendered
the QR. An attacker can load the real site's pairing page themselves, get a real signed request, and
re-render that exact QR anywhere — their own page, an email, a poster. Every check on the payload
itself (a proof-of-possession signature, an origin string) passes cleanly, because it genuinely is the
real site's real request, just relayed. This is the same class of attack that has hit WhatsApp Web's QR
login in the wild.

**The fix is a device code, not different crypto.** The website displays a short, human-typeable code
instead of a QR. The user reads it off the site they are actively looking at and types it into their
own OctoBot app. This removes the passive, at-scale version of the relay attack — a QR image posted
anywhere, scanned later, by anyone — because the code only has value for the few minutes it's valid,
read directly off a live page. It does not make a live, real-time relay attempt impossible in the
abstract, which is why the request/code carries a short expiry (`ttlSec`, default 5 minutes) rather
than a long one. **`expiresAt`/`createdAt` are not covered by `popSig`** — anyone with the code can
rewrite them — so "short" is enforced independent of what a request claims, and independent of
`createdAt` too: `createPairingRequest()` clamps `ttlSec` to a 1-hour maximum, and
`parsePairingRequest()` separately rejects any request whose `expiresAt` is more than that same
maximum away from the **real wall clock at verification time** — not from the request's own claimed
`createdAt`, which a party rewriting the record could otherwise co-forge alongside `expiresAt` to
keep the *declared* window narrow while placing both timestamps arbitrarily far in the future (making
an old, indefinitely-reusable code look freshly issued no matter when it's actually redeemed).

**A live space-member grant, not a data snapshot.** The website never receives a node credential, and
it never receives a one-time export either. Approving a request invites the website's ephemeral device
into the user's **cloud mirror** — a dedicated Starfish space the wallet (or its node, when one is
configured) keeps continuously synced with a read-only projection of the user's own data — as a
`space:member`. That membership is what the website actually reads through: every poll is a live pull
against the mirror, decrypted client-side with the space's own keyring, never a value handed over once
and then stale. Populating the mirror itself (which collections sync, how often, from which side —
wallet or node) is a separate concern from pairing a website to read it; this page only covers the
latter. `syncCloudMirror()` (exported from this package) and `MIRROR_COLLECTIONS` are the entry points
if you need to look at how the mirror gets written.

## The loop

1. The website calls `startPairingRequest()`, publishes the request, and displays the code.
2. The user opens their OctoBot app, enters the code.
3. The app calls `fetchPairingRequestByCode()` — which returns both the request and the pulled
   document's `hash` — shows the user what site is asking, and — on approval — calls
   `mintPairingGrant()` (inviting the website's device into the mirror space) and
   `publishPairingGrant()` (sealing the invite bundle to the website's ephemeral key, published
   with `baseHash` set to the request's `hash` from step 3's lookup — this is what makes "claim
   this exact request" atomic; see [Transport](#transport)).
4. The website, having been polling with `awaitPairingGrant()`, unseals the grant and immediately does
   a live read of every mirror collection it covers.

```ts
// Website side
import { startPairingRequest, awaitPairingGrant } from '@drakkar.software/octobot-client'

const rendezvous = { baseUrl: 'https://sync.drakkar.software/sync', namespace: 'dk' }
const session = await startPairingRequest({
  origin: 'https://myapp.example',
  rendezvous,
})
await session.publish()
showCodeToUser(session.code)                 // an 8-character code, e.g. "K7M3PQXR"

// `session` already carries its own `rendezvous` (spread it, or pass session
// directly — both work).
const result = await awaitPairingGrant(session, { timeoutMs: 5 * 60_000 })
console.log(result.collections['user-accounts'], result.collections['user-strategies'])

// Poll again any time to see the latest write — this is a live read, not a
// one-time export. `fetchPairingGrant` does the same live pull `awaitPairingGrant`
// did, just without the wait loop; pass the sealer you recorded above to pin it.
import { fetchPairingGrant } from '@drakkar.software/octobot-client'
const refreshed = await fetchPairingGrant(session, { expectedSealer: result.sealedBy })
```

`session` holds live key material (`session.device.kemPriv`, needed both to unseal the grant bundle
and to open the mirror space's keyring afterward) as a plain in-memory object — treat it with the same
care as any other secret if your app needs it to survive past the current request (e.g. an SSR round
trip). Don't persist it under a predictable key; tie it to an already-authenticated visitor identity if
it must be stored at all.

```ts
// Phone side (what an app embedding octobot-client + octobot-sdk does)
const request = await sync.websitePairing.lookupRequest(codeTheUserTyped)
// show request.origin, request.label to the user for confirmation
const paired = await sync.websitePairing.approve(request)
console.log(paired.grantedCollections) // e.g. ['user-accounts', 'user-strategies']
```

`approve()` throws `NothingToShareError` if the wallet has never mirrored anything yet — there is
nothing worth inviting the website to read. The SDK's own `approve()` self-heals this: it triggers one
mirror sync of the default collections and retries the mint, so from the app's point of view "approve"
just works the first time too, as long as the wallet is online. A bare `octobot-client` integration
that calls `mintPairingGrant()` directly does not get this retry for free — run
`syncCloudMirror()`/your own mirror writer at least once first.

## What a grant covers, and what it deliberately does not

A grant is a real `space:member` cap on the wallet's **shared** mirror space — never the private one,
and never `user-accounts-auth` (exchange credentials), which the mirror never writes to any space at
all, at any layer. It covers every collection that is both third-party eligible — `visibility` other
than `"private"`, i.e. `isThirdPartyEligible(id)` (see
`MIRROR_COLLECTIONS`) — and **actually has a mirror node at mint time**: a collection the user has
enabled for cloud sync but that hasn't synced yet simply isn't there to invite into.

**Mirrored data is the raw synced document, not a curated field allowlist.** Unlike the old
sealed-snapshot design this replaces, the mirror does not project through
`ACCOUNT_SNAPSHOT_FIELDS`/`AUTOMATION_SNAPSHOT_FIELDS`/`STRATEGY_SNAPSHOT_FIELDS`-style allowlists —
each collection ships the same document the writer's own local store holds. Decide what to mirror at
the `cloudSyncEnabled`/`cloudSyncCollections` layer (per collection, before anything is written), not
by assuming a website only ever sees a hand-picked subset of a collection's fields once that
collection is enabled.

**This is a live feed, not a point-in-time export.** There is no `generatedAt` watermark to render as
"data as of …" — call `readMirrorCollections()` again whenever you want the latest state. Freshness is
bounded by whether the wallet (or its node) is online and has recently run its mirror sync, not by
anything the grant itself carries.

## Origin verification is the caller's responsibility, and is not yet built into this package

`origin` in a pairing request is an attacker-authorable string — anyone can put any value there. This
package does not verify it. An app embedding this on the phone side should not present `origin` as a
verified identity without doing that verification itself, and should say plainly and prominently in
its UI when it hasn't — not as a small aside easy to miss.

**The `.well-known` convention.** A site can serve `/.well-known/octobot-pairing.json` over HTTPS
from the exact origin it declares in its pairing request:

```json
{
  "octobotPairing": true,
  "label": "My Trading Dashboard"
}
```

`label` should match the `label` the site passes to `startPairingRequest()`. This is a same-origin
reachability and label-consistency check, not a cryptographic proof of identity — it confirms the
declared origin is reachable and self-consistent, not that it's trustworthy. It rules out the
simplest form of spoofing (a site that declares an origin it doesn't actually control, and never
serves this file from it) without claiming to solve origin verification in general.

**This file is not yet checked by any client in this package.** It's documented now so site operators
can start serving it ahead of the verifying code landing, and so an embedding app's future
verification step has a fixed target to implement against, rather than needing to invent (and every
integrator separately reinventing) its own convention.

## `requesterKind`: a website isn't the only thing that can be on the other end

The device-code flow was designed for a website, but nothing about it is actually website-specific —
the requester just needs to publish a request, show the code, and unseal whatever grant comes back.
`PairingRequestPayload.requesterKind: 'website' | 'device'` names which kind of thing is asking:

- `'website'` — the original case. `origin` is a URL, and the trust question is "does this domain
  really control the origin it claims" (see above).
- `'device'` — another OctoBot client (e.g. a second phone) pairing as a read-only viewer of this
  wallet's cloud mirror. There is no domain to spoof here — the human relaying the code between two
  devices they hold *is* the trust anchor, the same way typing a pairing code into a website is.
  `origin` verification (and the `.well-known` convention above) simply doesn't apply to this case.

`createPairingRequest`/`startPairingRequest` default `requesterKind` to `'website'` when not passed,
but the built payload always carries the field — `parsePairingRequest` rejects one that's missing it.
An approving UI should branch its copy on this field rather than assuming every request is a website;
mobile2's `website-pairing-approve.tsx` is the reference implementation (device requests skip the
origin-unverified warning and show the request's `label` instead of a URL).

## Trust-on-first-use pinning across refreshes

`fetchPairingGrant()` returns `sealedBy` — the Ed25519 pubkey that actually sealed the grant, verified
via the wrap entry's signature, never merely claimed. A website should record this after its first
successful read and pass it back as `expectedSealer` on every later poll for the same session.
`_pairing`-style rendezvous collections are public-write, so a second party who somehow learns the code
could otherwise overwrite an already-established pairing's grant slot with their own — the pin turns
that into a hard failure instead of a silent identity switch.

**A replayed grant blob is far less dangerous here than a replayed snapshot was.** The old
sealed-snapshot design needed an explicit freshness watermark (`afterGeneratedAt`) because a replayed
old blob was, on its own, indistinguishable from a legitimate update — the snapshot carried no live
authority check, only its own signature. A grant is different: the cap it carries only works while the
website's ephemeral device is still a member of the mirror space. `unpairWebsite()`/`revokePairingGrant()`
removes that membership immediately and directly — so even a perfectly replayed, correctly-signed old
grant blob fails the moment a website actually tries to use it to read, because the read itself is a
live, node-enforced space-membership check, not just a check on the blob. There is currently no
`afterGeneratedAt`-equivalent on `fetchPairingGrant()`/`awaitPairingGrant()` — none is needed for this
reason, not because the check was overlooked.

**The very first resolution has nothing to pin against yet.** `expectedSealer` protects every read
*after* the first one — the first successful `fetchPairingGrant()` call for a session trusts whatever
`sealedBy` it sees outright, because there is no prior pin to check it against. If two different
parties race to answer a session's very first request, whichever one's publish is read first wins,
silently. This package does not add extra latency (e.g. waiting an extra poll cycle to catch a second,
different `sealedBy` arriving right after the first) to close that window — a real design option, but
one that changes `awaitPairingGrant()`'s documented behavior and timing for a narrow race that's
already bounded by the code's short live window.

**Every publish after the first is now tamper-evident, not tamper-proof.** `pushRendezvousDoc()`
writes against the caller's *own* remembered hash (`baseHash`), not "whatever the server currently
has" — so a third party who overwrites the `joinsessions` slot is no longer silently adopted as the
new legitimate baseline by the next legitimate write. That write now fails with a named "modified"
error instead. This is also exactly the mechanism `publishPairingGrant()` relies on to claim a request
atomically (see [Transport](#transport)): the phone's grant write uses the request's own pulled
`hash` as `baseHash`, so if the request was swapped between the phone's read and its grant write, the
write fails loudly instead of sealing a grant to the wrong device. The residual gap: a hostile write
landing between two legitimate writes is invisible *until* that next write is attempted — this
converts what used to be a silent, undetectable hijack forever into one race window, then a loud,
unmissable failure. **This is a compare-and-swap against a specific document version, not proof of
who wrote it** — anyone can still publish a *self-consistent* replacement request (freshly generated
keys, correctly self-signed, same `origin`/`label` text) to a slot before the legitimate phone reads
it; `baseHash` only protects against tampering *after* a caller's own read, not against a swap that
happens entirely before it. Origin verification (above) is what actually helps there, not this
mechanism.

## Unpairing

`revokePairingGrant()` (surfaced as `sync.websitePairing.unpair()` on the phone) removes the paired
website's ephemeral device from the mirror space's member roster, and `clearPairingGrant()` wipes the
`joinsessions` slot the request and grant share — since the two phases now live at one address,
clearing it clears both together; there's no way to keep one and drop the other. This is **real,
immediate revocation** — the next read the website attempts fails live at the node, because access is
a real space-membership check performed on every request, not a cached decision. The one honest
residual: this cannot erase what the website already fetched and decrypted before the revocation — a
decrypted value, once read into a third party's page, is an ordinary value that page can log or
persist, and there is no way to reach into a website's memory. Any UI built on this must say "revoked"
for what it actually is, but should not claim past reads are somehow undone.

## Refreshing

`sync.websitePairing.refresh(id)` re-mints against the current state of the mirror (useful after the
user enables another collection for cloud sync, so an already-paired site's grant picks up the new
coverage without a full unpair/re-approve). A bare `octobot-client` integration does the equivalent by
calling `mintPairingGrant()` again and re-publishing with `publishPairingGrant()`, passing the `hash`
its own *previous* `publishPairingGrant()` call returned as `baseHash` — not the request's original
hash, and not `null`.

## Transport

The rendezvous is a single collection, `joinsessions` (`_pairing/session/{code}`) — distinct from the
QR-pairing flow's `_pairing` collection, which is far too small (16 KB) and has no TTL. **One address
serves both phases of the exchange, keyed throughout by the same human-typeable `code`**: the
website's "request" doc, and the phone's "grant" doc that later overwrites it in place.

The two phases are told apart on the wire by an unsealed top-level `kind` field — `'octobot-pairing-request'`
for the discovery phase, or `'octobot-pairing-grant'` for the delivery phase (which wraps the actual
sealed blob: `{v: 1, kind: 'octobot-pairing-grant', sealed: <SealedBlob>}`) — so a poller can tell
"still waiting" from "approved" without attempting to unseal anything. `fetchPairingRequestByCode()`
and `fetchPairingGrant()` both handle this internally; you never need to inspect `kind` yourself.

**Claiming a request is a compare-and-swap, not a blind overwrite.** `fetchPairingRequestByCode()`
returns the pulled document's `hash` alongside the parsed request. `publishPairingGrant()`'s
`baseHash` on first publish must be exactly that hash — the write only succeeds if the slot still
holds precisely the request doc the phone read, so a request that was swapped or already claimed
between the read and the write is detected as a conflict (`OctoBotConflictError`) instead of silently
overwritten. There is no `baseHash: null` "fresh slot" case here the way the retired two-address
design had one for the grant — the slot is never empty by the time a caller reaches
`publishPairingGrant()`, it already holds the request.

Merging the two phases into one address does not weaken confidentiality: the old
`pairingsnapshots` collection was already public-read regardless of its address entropy, and the old
`pairingrequests` doc carried the session id in plaintext, so guessing the code already yielded the
session address for free. The real confidentiality boundary was always that the grant is sealed to
the website's ephemeral KEM key, which never leaves the browser — an address split provided no
protection the seal didn't already provide, only lifecycle bookkeeping this merge no longer needs.

The collection is public read/write, reached through a cap-less `StarfishClient` this package builds
internally; nothing here needs a seed or a cap for the request/grant exchange itself. Reading the
mirror once a grant is unsealed is a separate, cap-authenticated connection (see
`ReadMirrorCollectionsOptions`).

Reaching the rendezvous from a browser page needs the page's origin allowlisted for CORS at the
infrastructure level — this is centrally managed (one allowlist for the shared sync server, not
per-node operator configuration the way direct node access would be), but it is still a real,
named dependency. A `*.drakkar.software` subdomain, `localhost`, or a bare IP-literal origin is
allowlisted by a wildcard already; anything else needs a one-time addition.
