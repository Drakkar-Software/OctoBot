# OctoBot Sync

OctoBot Sync is the server component that lets OctoBot nodes act as personal sync endpoints. It is built on top of [Starfish](https://github.com/Drakkar-Software/starfish-server), which provides the collection routing and storage abstractions. OctoBot Sync layers on top of Starfish the wallet-based authentication, the collection schema for user data, and the glue that connects it all to the rest of OctoBot.

## How it fits together

When OctoBot runs with the node interface enabled, the sync app is mounted inside the main FastAPI application at `/sync`. All requests to `/sync/v1/…` are forwarded to the Starfish router, which handles pull, push, list, and batch operations against collections of encrypted documents.

Starfish routes requests to the right collection based on the URL path. Each collection declares which roles may read or write it, how its storage key is derived (a path template like `users/{identity}/data`), and what encryption scheme applies. OctoBot's default collections (`user-data`, `user-accounts`, `user-settings`, `user-strategies`) are defined in `sync/collections.py` and all use identity-based encryption, meaning data is encrypted with a key derived from the wallet address of the owner.

The sync app wraps Starfish with `NamespaceRewriteMiddleware`. This middleware rewrites incoming URLs of the form `/<namespace>/<version>/…` into `/<version>/<namespace>/…` before they reach the Starfish router. This allows clients that group requests by namespace first (the community server format) to talk to the same server that routes by version first.

## Wallet authentication and the signature scheme

Every request must carry a valid ECDSA signature proving ownership of an Ethereum wallet. The server recovers the signer's address from the signature and compares it against the `X-Starfish-Pubkey` header. Starfish then evaluates the recovered identity against the collection's role rules.

### Why this design

Using secp256k1 signatures means any existing Ethereum wallet — hardware or software — can authenticate without a separate credential. The server never stores secrets, never issues tokens, and never needs a session. The client proves ownership on every request.

To prevent replay attacks, each request includes a timestamp (within a 10-second window of the server clock) and a UUID nonce. The server stores seen nonces and rejects duplicates.

### Canonical string

The message that is signed is a deterministic string with six newline-separated fields:

```
ED25519-OCTOBOT
{METHOD}
{path}
{timestamp}
{nonce}
{bodyHash}
```

- `METHOD` is the HTTP verb in uppercase.
- `path` is the request path as seen by the server after any mount prefix is stripped. For a node deployment this is `/v1/octobot/pull/users/{address}/data` — the same path the Starfish router routes against.
- `timestamp` is `Date.now()` as a decimal millisecond string.
- `nonce` is a UUID generated per request.
- `bodyHash` is the lowercase hex SHA-256 of the UTF-8 request body, or the SHA-256 of an empty string for requests with no body.

### EIP-191 wrapping

The canonical string is signed as an Ethereum personal message (EIP-191 version `0x45`). The bytes that are actually hashed and signed are:

```
keccak256( "\x19Ethereum Signed Message:\n" + byteLength(canonical) + canonical )
```

where `byteLength` is the UTF-8 byte count of the canonical string. This is the format produced by `eth_account.encode_defunct` and by `ethers.signMessage` on the client side. A common mistake is to construct the `SignableMessage` struct with `version = b"\x19"` directly: because `eth_account._hash_eip191_message` prepends `\x19` before the version byte, that produces a double-prefix hash (`\x19\x19…`) and recovers the wrong address.

### Path matching

The server uses `request.scope["path"]` (Starlette's ASGI path) and strips `scope["root_path"]` when it is a prefix of the path. When the sync app is mounted at `/sync` by the node interface, Starlette's `Mount` already strips `/sync` from `scope["path"]` and sets `scope["root_path"] = "/sync"`. The role resolver therefore sees `/v1/octobot/pull/…` — the path the client signs against — without needing special-case logic for the mount point.

## Collection configuration

Collections are loaded from `user/collections.json` at startup. If that file is absent the server falls back to `DEFAULT_SYNC_CONFIG`, which defines the four standard user collections. The file follows the Starfish `SyncConfig` schema; namespaced collections go under the `namespaces` key rather than the top-level `collections` key.

A collection whose `storagePath` contains no template parameters (no `{…}`) is treated as replicable — it can be mirrored between nodes. Collections parameterised on `{identity}` are private to the owning wallet.
