---
title: "Wire Contract"
description: "Every literal string the client shares with the node's Python sync implementation — bootstrap challenge, HKDF salt, collection paths, and per-collection encryption info strings."
sidebar_position: 14
---

# Wire contract

Every literal below is shared with the node's Python implementation in this same repo
(`packages/sync/octobot_sync/`). **A mismatch on either side breaks sync silently** — no error, just
data that never syncs, or that syncs under the wrong identity. `tests/wireContract.test.ts` pins all
of these; if you're changing one on purpose, update both sides in the same change and check the test
still documents what actually shipped.

| Constant | Value | TS location | Python source |
|---|---|---|---|
| Bootstrap challenge | `'octobot:sync-bootstrap'` | `identity/capProvider.ts::BOOTSTRAP_CHALLENGE` | `constants.py::SYNC_BOOTSTRAP_CHALLENGE` |
| HKDF salt | `'octobot-starfish-identity-v1'` | `crypto/wireConstants.ts::STARFISH_ENCRYPTION_SALT` | `constants.py::HKDF_SALT_STRING` |
| Sync mount path | `'sync'` | `crypto/wireConstants.ts::SYNC_MOUNT_PATH` | the app's sync sub-app mount |
| Sync namespace | `'octobot'` | `crypto/wireConstants.ts::SYNC_NAMESPACE` | the Starfish namespace this node registers under |
| Node REST prefix | `'/api/v1'` | `transport/constants.ts::API_PREFIX` | the node's FastAPI router prefix |
| Default node port | `5001` | `transport/constants.ts::DEFAULT_NODE_PORT` | the node's default listen port |
| Blob envelope keys | `{ iv, data }` | `crypto/secretEncryptor.ts` | `crypto.py::BLOB_IV_KEY` / `BLOB_DATA_KEY` |
| AES-GCM IV length | 12 bytes | `crypto/secretEncryptor.ts::IV_BYTES` | `crypto.py::IV_BYTES` |

## Collection paths and per-collection HKDF `info`

Each collection's `encryptionInfo` MUST equal `'octobot-sync-' + <node's Collections enum value>` —
the node derives its per-collection key from this exact string.

| Collection key | Storage path | `encryptionInfo` | Python `Collections` enum value |
|---|---|---|---|
| `userData` | `users/{identity}/data` | `octobot-sync-user-data` | `user-data` |
| `accounts` | `users/{identity}/accounts` | `octobot-sync-user-accounts` | `user-accounts` |
| `settings` | `users/{identity}/settings` | `octobot-sync-user-settings` | `user-settings` |
| `strategies` | `users/{identity}/strategies` | `octobot-sync-user-strategies` | `user-strategies` |
| `actions` | `users/{identity}/actions` | `octobot-sync-user-actions` | `user-actions` |
| `accountTrading` | `users/{identity}/accounts/{accountId}/trading` | `octobot-sync-user-accounts-trading` | `user-accounts-trading` |

Source of truth for the Python side: `packages/sync/octobot_sync/enums.py::Collections`.

## Pairing wire literals

Separate from the node's own collections above — the device-code website-pairing flow (see
[Website pairing](website-pairing.md)) uses its own rendezvous path and payload markers:

| Constant | Value | TS location |
|---|---|---|
| Join session path | `_pairing/session/{code}` | `transport/rendezvous.ts` |
| Pairing request payload kind | `'octobot-pairing-request'` | `identity/pairingRequest.ts` |
| Pairing request payload version | `1` | `identity/pairingRequest.ts` |
| Join session grant document kind | `'octobot-pairing-grant'` | `client/pairing/pairingGrantExchange.ts` |
| Join session grant document version | `1` | `client/pairing/pairingGrantExchange.ts` |

The request payload also carries a required `requesterKind: 'website' | 'device'` field
(`identity/pairingRequest.ts`) — `'website'` for the original case (a third-party site running this
package in a browser), `'device'` for another OctoBot client (e.g. a second phone) pairing as a
read-only viewer of this wallet's cloud mirror. `createPairingRequest`/`startPairingRequest` default it
to `'website'` when not passed, but it is always present on the wire — there is no absent-means-website
fallback in `parsePairingRequest`, which rejects a payload missing it. The approving side branches its
copy on this field: a `'device'` request has no real "origin" to verify (see mobile2's
`website-pairing-approve.tsx`), trust instead comes from the human typing the code themselves.

**One address serves both phases**, keyed throughout by the same human-typeable `code` — the website's
"request" document, later overwritten in place by the phone's "grant" document. The two are told apart
on the wire by the top-level `kind` field: `'octobot-pairing-request'` for the request phase (fields
unsealed — public keys and `origin`, nothing confidential), or `'octobot-pairing-grant'` for the grant
phase, which wraps the actual encrypted payload: `{v: 1, kind: 'octobot-pairing-grant', sealed:
<SealedBlob>}`. The `kind`/`v` on this OUTER wrapper are plaintext on the wire deliberately — a poller
needs to distinguish "still just a request" from "a grant has been published" without attempting
`unseal()` on a document that might not even be sealed yet. This replaces the retired two-collection,
two-address design (`pairingrequests` at `_pairing/requests/{code}`, `pairingsnapshots` at
`_pairing/snapshots/{sessionId}`) — merging was safe because the old high-entropy session address
bought no real confidentiality the grant's own sealing didn't already provide (see
[Website pairing](website-pairing.md)'s Transport section for the full argument).

`tests/wireContract.test.ts`'s `'wire contract: device-code pairing (rendezvous)'` describe block pins
the path, the request kind/version, and the grant document's outer kind/version/`sealed` shape. Note
this is a DIFFERENT payload from the QR read-only pairing flow's own `'octobot-read-only-pairing'` kind
(pinned separately, in that same test file's `'wire contract: QR read-only pairing'` block) — the flows
are distinct mechanisms (see [Website pairing](website-pairing.md)'s intro for why) and do not share
wire literals.

The path is public read/write, and claiming a request is a compare-and-swap: `publishPairingGrant()`'s
`baseHash` on first publish must be the exact `hash` `fetchPairingRequestByCode()` returned alongside
the request it read, so a request swapped or already claimed between the read and the write is
detected as a conflict rather than silently overwritten (`pushRendezvousDoc()`'s `baseHash` mechanism).
A party that captures the human code during its short live window can still publish a
self-consistent replacement request before the legitimate device reads it — that race is inherent to a
human-typed code and not closeable by this compare-and-swap alone (it only protects a caller's OWN
subsequent writes, not a swap that happens entirely before its first read); see
[Website pairing](website-pairing.md) for the full model, including why origin verification is the
actual defense for that case.

## Why this page exists

Every one of these strings is duplicated, by necessity, on both sides of the wire — TypeScript
cannot import Python constants. The single highest-value thing a change to `packages/sync/` or this
package can do is check this table (and re-run `tests/wireContract.test.ts`) before merging.
