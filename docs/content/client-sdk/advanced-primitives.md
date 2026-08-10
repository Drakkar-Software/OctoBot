---
title: "Advanced: Building an Offline Layer on Top"
description: "The tier-1 subpath exports (identity, transport, crypto, collections, protocol, node-api), the layering rule, and the DI seam for the two-phase automation race, for callers building their own persistence/offline/CRDT layer."
sidebar_position: 13
---

# Advanced: building an offline layer on top

This page is for a caller building persistence, an offline queue, or CRDT merge across devices on
top of this package — `@drakkar.software/octobot-sdk` (the OctoBot Cloud app's own sync engine) is
the worked example.

## Use the subpath exports, not `client/`

```
@drakkar.software/octobot-client            → the facade (connectOctoBot, strategy, errors)
@drakkar.software/octobot-client/identity   → WalletCapProvider, key derivation, mnemonic tools
@drakkar.software/octobot-client/transport  → node REST client, sync client factory, node detection
@drakkar.software/octobot-client/crypto     → the secret encryptor, wire constants
@drakkar.software/octobot-client/collections → the node collection registry, path helpers
@drakkar.software/octobot-client/protocol   → pure builders/parsers, the strategy module, the DI'd
                                               two-phase automation orchestration
@drakkar.software/octobot-client/node-api   → the raw node REST fetchers
```

**The layering rule this package enforces on itself** (see `tests/layering.test.ts`): nothing under
these subpaths ever imports `client/`. Building your own offline layer on `client/` instead of these
would give you a second key-derivation cache, a second cap-provider lifecycle, and a second request
path to the same node running alongside whatever caching/retry logic you build — two systems talking
to one node with different retry semantics. Consume the primitives directly and own your own
caching/lifecycle, the way `octobot-sdk` does.

## The DI seam for the two-phase automation race

`protocol/orchestration/createAutomation.ts::runCreateAutomation(io, input, opts)` takes an
`ActionEmitter — { emit, poll }` you implement:

```ts
const io: ActionEmitter = {
  emit: (configuration) => myOutbox.append(configuration), // returns the action's id
  poll: async () => {
    await myOutbox.drain()
    await myUserDataStore.pull()
    return parseNodeUserActions(myUserDataStore.data)
  },
}
const { automationId } = await runCreateAutomation(io, input)
```

This is the SAME state machine `connectOctoBot()`'s facade uses (wired to a direct append + pull) —
one implementation of the strategy-then-automation race fix, reused instead of re-derived.

## Reference stability matters for `useSyncExternalStore`

`protocol/state.ts`'s parsers (`parseNodeAutomationStates`, `parseNodeAccounts`, etc) are memoized
per input document reference (`cachedByDoc`, an internal `WeakMap`). If you read through a
`useSyncExternalStore`-style selector, a fresh `.filter()`/`.map()` on every call trips React's
"getSnapshot should be cached" infinite-loop guard — these parsers return the SAME array reference
for the same document object, and a new reference only appears when your store actually replaces the
document. Preserve this property in anything you build on top: don't rebuild an array from these
parsers' output on every render.

## Local-domain adapters are your job, not this package's

Functions that merge node state into a caller's own local, CRDT-tombstoned domain objects (an
`Account` type with `deletedAt`/`editedAt`, UI-only display fields, kinds the protocol doesn't model)
are deliberately NOT in this package — see `protocol/state.ts`'s exports for the pure half and write
your own `accountFromNodeState(protocolAccount, priorLocalAccount)`-shaped adapter for the merge half.
`octobot-sdk`'s `src/adapters/` is the reference implementation.
