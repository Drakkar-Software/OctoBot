---
title: "Collections and Encryption"
description: "The node's collections and their paths, the AES-256-GCM document envelope, and the raw documents escape hatch for unmodeled collections."
sidebar_position: 10
---

# Collections and encryption

## The node's collections

| Key | Path | Encryption | Pull/push |
|---|---|---|---|
| `userData` | `users/{identity}/data` | identity | pull; automations/user_actions are node-computed, other fields are whatever else you store there |
| `accounts` | `users/{identity}/accounts` | identity | pull-only from the node's side (`accounts`/`exchange_configs`) |
| `settings` | `users/{identity}/settings` | identity | pull + push, opaque |
| `strategies` | `users/{identity}/strategies` | identity | legacy/unused by the node directly — strategies live in the action history instead |
| `actions` | `users/{identity}/actions` | identity | push/append-only |
| `accountTrading` | `users/{identity}/accounts/{accountId}/trading` | identity | pull-only, one document per account |

Full path→HKDF-info table: [Wire contract](wire-contract.md).

## The envelope

Every document body is `{ iv: base64, data: base64 }`:

1. `deriveKey(encryptionSecret, salt, info)` → HKDF-SHA256 → a 256-bit AES key. `salt` is the fixed
   `STARFISH_ENCRYPTION_SALT`; `info` is the per-collection string (`'octobot-sync-user-accounts'`,
   etc) — this is what makes each collection's key independent even though they all derive from the
   same wallet secret.
2. A random 12-byte IV, AES-256-GCM encrypt the JSON-serialized document.
3. Base64-encode both, wrap as `{ iv, data }`.

Decryption is the inverse. `crypto/secretEncryptor.ts::createSecretEncryptor(secret, salt, info)`
returns an `Encryptor` with `.encrypt()`/`.decrypt()`, memoizing the derived key.

## Using the escape hatch for a collection this package doesn't model

```ts
const { data, hash } = await octobot.documents.pull('settings')
await octobot.documents.push('settings', { ...data, myField: 1 }, { baseHash: hash })
```

For a collection outside the `NodeCollectionKey` union entirely, use `documents.raw`:

```ts
const encryptor = await octobot.documents.raw.encryptorFor('settings') // or build your own info string
const path = octobot.documents.raw.pullPath('settings')
const result = await octobot.documents.raw.sync.pull(path)
```
