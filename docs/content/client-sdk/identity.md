---
title: "Identity"
description: "How a private key (or a BIP39 mnemonic that derives one) deterministically derives your node identity, address, and encryption key in the OctoBot client SDK — and the chain, walked step by step."
sidebar_position: 2
mdx:
  format: mdx
---

import DemoEmbed from '@site/src/components/demo/Embed';

# Identity

This is the page to read before anything mysteriously doesn't sync.

<DemoEmbed section="derive" />

## There is no login — the wallet IS the identity

A raw secp256k1 private key (`0x`-prefixed, 64 hex characters) resolves through one deterministic
chain, entirely in your process, with zero network calls:

```
private key  →  secp256k1 pubkey  →  EIP-55 address
             →  EIP-191 personal_sign('octobot:sync-bootstrap')
             →  HKDF-expand  →  Ed25519 + X25519 root identity
             →  userId = hex(sha256(rootEdPub))[:32]   ← 32 HEX CHARS = 16 bytes, not 32 bytes
             →  users/{userId}/accounts   ← the literal path every read uses
```

You can also start from a BIP39 mnemonic instead of a raw key — `connectOctoBot`'s `seed` option
accepts either. A mnemonic derives a private key first, via standard `m/44'/60'/0'/0/0`, then joins
the exact same chain above — see "Deriving from a mnemonic instead" below.

The node authorizes requests by the Starfish identity (the Ed25519/X25519 keypair), which is
entirely determined by which private key came out of the first arrow. Two different derivations of
the "same" key material produce two completely different identities, two different addresses, and
two completely disjoint sets of synced data — see "The failure mode is silent" below.

**Concretely, in code:**

```ts
import { deriveBip44PrivateKey, deriveEvmAddress, deriveRoot } from '@drakkar.software/octobot-client/identity'

const privateKey = await deriveBip44PrivateKey(rawPrivateKeyHex) // already a key — passed through unchanged
const address = deriveEvmAddress(hexToBytes(privateKey))         // EIP-55 checksummed
const root = await deriveRoot(rawPrivateKeyHex, 'bip44')         // signs the bootstrap challenge, HKDF-expands
console.log(root.userId)                                         // hex(sha256(root.keys.edPub)).slice(0, 32)
```

`root.userId` is NOT the EVM address — it's the `{identity}` URL segment every collection path uses
(`users/{identity}/accounts`, etc). And the same EVM private key, hex-encoded, doubles as the
**encryption secret**: every document is AES-256-GCM encrypted with a key HKDF-derived from it. One
chain produces both "who the node thinks you are" and "what can decrypt your data" — there's no
second key to lose track of.

## The failure mode is silent

This only applies if you start from a mnemonic — a raw private key has no scheme to get wrong (see
"Deriving from a mnemonic instead" below). `connectOctoBot` doesn't crash if the wrong derivation is
picked — it authenticates against the node under a wallet the node has never seen, and every read
comes back **empty**, not with an error. The same mnemonic, derived two different ways, looks exactly
like this:

```
bip44            → userId a3f9c2e1b6d84f07c5e0912ab34fd678   (the node knows this wallet)
some-other-way   → userId 7c0491de5a3fb2891066cd45e9021acf   (the node has never seen this one)
```

Pick the second one against a real node and every call still succeeds — it just authenticates as a
wallet the node has never heard of. With `verify: true` (the default) this surfaces immediately as an
`OctoBotAuthError`, whose message names the address that was tried and suggests the fix. With
`verify: false` you won't find out until your first real call returns nothing:

```ts
try {
  await connectOctoBot({ url, seed })
} catch (err) {
  if (err instanceof OctoBotAuthError) {
    console.error(`node did not authorize ${err.address} (${err.derivation})`)
    // retry with { seedDerivation: 'auto' } if more than one scheme is registered
  }
}
```

## Derivation schemes

`seedDerivation` names a scheme registered in a small registry (`identity/derivationSchemes.ts`),
not a fixed enum. `'bip44'` (standard `m/44'/60'/0'/0/0`) is the only one this package ships, and
the default — it's what an OctoBot node's own pairing QR, MetaMask, or any standard wallet uses.

| `seedDerivation` | Path | Use it when |
|---|---|---|
| `'bip44'` (default) | Standard `m/44'/60'/0'/0/0` | Always, unless you've registered another scheme. |
| `'auto'` | Tries every registered scheme in turn | You don't know which one applies — only useful once more than one scheme is registered. Costs one extra round-trip per scheme tried; requires `verify: true` (the default). |

A caller integrating a different wallet type (another chain, a hardware-wallet-derived key, …)
registers its own scheme via `registerDerivationScheme({ id, derive })` and passes that `id` as
`seedDerivation`. An unregistered id throws `unknown derivation scheme` immediately, rather than
silently deriving under the wrong scheme.

## Deriving from a mnemonic instead

If `seed` is already a `0x`-prefixed 64-hex private key, every derivation scheme is a no-op — the
key passes through unchanged, and `seedDerivation` is irrelevant. If instead you pass a BIP39
mnemonic, the scheme picked by `seedDerivation` is what turns it into that private key —
`deriveBip44PrivateKey`/standard `m/44'/60'/0'/0/0` by default. Both inputs join the exact same chain
from that point on.

## What a device cap-cert actually is

Every sync request is signed with a **short-lived device capability**, minted fresh per request from
the root Ed25519 key (`scopes.rootAll()` — full access under this identity). This mirrors the node's
own `WalletCapProvider` (`packages/sync/octobot_sync/auth/provider.py`) exactly: the client never
sends a long-lived bearer token, and a captured cap-cert is worthless after it expires.

## Pairing-QR shapes

A node's "Pair mobile device" QR encodes `{ url, address, password }` or, on an older node,
`{ url, address, passphrase }`. The field name is what distinguishes them:

- `password` — the wallet itself (a phrase or key). No network round-trip needed to import it.
- `passphrase` — an HTTP Basic password for the node's REST API; the wallet still has to be fetched
  separately via `client.node.exportWallet()` (which needs that same Basic auth) — see
  [Node REST API](node-rest-api.md).
