---
title: "Escape Hatches"
description: "The paved path's five ways out: custom fetch for proxies/mTLS/React Native, verify:false, raw documents for unmodeled collections, seedDerivation:'auto', and the version compatibility table."
sidebar_position: 12
mdx:
  format: mdx
---

import DemoEmbed from '@site/src/components/demo/Embed';

# Escape hatches

Everything in the other pages is the paved path. These are the ways out of it — for proxies, for
collections this package hasn't wrapped yet, for skipping I/O you don't want, and for knowing which
node you can actually talk to.

<DemoEmbed section="escape-hatches" />

## Custom `fetch`

`ConnectOptions.fetch` — for proxies, mTLS, or a React Native crypto/fetch polyfill.

```ts
const octobot = await connectOctoBot({ url, seed, fetch: myProxyAwareFetch })
```

## `verify: false`

Skips the connect-time probe. `connectOctoBot()` then does zero I/O, and the first real call (e.g.
`accounts.list()`) surfaces any connectivity or auth problem lazily instead.

```ts
const octobot = await connectOctoBot({ url, seed, verify: false })
```

## Raw documents — `client.documents`

Escape hatch for any collection this package's typed facades don't cover, typed loosely. See
[Collections and encryption](collections-and-encryption.md) for the full shape and an example.
`client.documents.raw` exposes the underlying `StarfishClient` and cap provider directly for anyone
building a lower-level integration.

## `seedDerivation: 'auto'`

Tries every scheme currently registered in the derivation-scheme registry — `bip44` is the only one
this package ships by default — and keeps whichever one the node authorizes. It's really only useful
once a consumer has registered a second scheme via `registerDerivationScheme` (from
`@drakkar.software/octobot-client/identity`, see [Identity](identity.md)) for a different wallet
type; with only `bip44` registered, `'auto'` and `'bip44'` behave identically except `'auto'` costs
an extra round-trip.

```ts
const octobot = await connectOctoBot({ url, seed, seedDerivation: 'auto' })
```

## Compatibility

| Package | Required version |
|---|---|
| This package | `0.3.0` |
| `@drakkar.software/octobot-protocol` | `^0.6.0` |
| Minimum node | protocol `0.4.0` |
| Minimum sync server (website pairing only) | must define the `joinsessions` collection (`_pairing/session/{code}`) — the `pairingrequests`/`pairingsnapshots` collections this package used before `0.3.0` no longer exist in this package's own code. Only [Website pairing](website-pairing.md) needs this; everything else on this page works against any compatible node/sync server regardless of this collection. |
