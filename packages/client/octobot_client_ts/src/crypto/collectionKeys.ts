import { deriveAesKeyBytes } from './hkdf.js'
import { STARFISH_ENCRYPTION_SALT } from './wireConstants.js'
import { toBase64, fromBase64 } from '../internal/bytes.js'
import { NODE_COLLECTIONS, type NodeCollectionKey } from '../collections/nodeCollections.js'

/** `"0x"`-strip, matching `secretEncryptor.ts`'s `normalizeSecret` — HKDF
 *  treats its secret as an opaque byte string, so the prefixed and
 *  unprefixed forms of the same key derive completely different bytes, and
 *  the node always HKDFs the stripped form. */
function normalizeSecret(secret: string): string {
  return secret.startsWith('0x') ? secret.slice(2) : secret
}

/**
 * Derive one base64-encoded, per-collection AES-256 key for each of
 * `collections`, from the wallet's derived encryption secret. Each key is
 * `HKDF-SHA256(secret, STARFISH_ENCRYPTION_SALT, collection.encryptionInfo)`
 * — the exact same derivation `createSecretEncryptor` performs internally,
 * just stopped one step early (raw bytes instead of an imported `CryptoKey`)
 * so the bytes can travel in a read-only pairing payload.
 *
 * One-way and collection-independent by construction: HKDF cannot be
 * inverted to recover `secret`, and a key derived for one `info` string
 * reveals nothing about a key derived for a different one — so a payload
 * carrying `{userData, accounts}` keys grants exactly those two collections,
 * never the wallet secret itself and never `settings`/`strategies`/
 * `accountTrading`, even though every collection's key is a deterministic
 * function of the same underlying secret.
 *
 * Returns a `Partial` record deliberately: a grant covers a subset of
 * collections, never all of them, and TypeScript should not let a caller
 * assume every key is present.
 */
export function deriveCollectionKeys(
  secret: string,
  collections: readonly NodeCollectionKey[],
): Partial<Record<NodeCollectionKey, string>> {
  const normalized = normalizeSecret(secret)
  const keys: Partial<Record<NodeCollectionKey, string>> = {}
  for (const collection of collections) {
    const info = NODE_COLLECTIONS[collection].encryptionInfo
    const bytes = deriveAesKeyBytes(normalized, STARFISH_ENCRYPTION_SALT, info)
    keys[collection] = toBase64(bytes)
  }
  return keys
}

/** Decode one collection's base64 key back to raw bytes, for
 *  `createRawKeyEncryptor`. Throws on malformed base64 or a length other
 *  than 32 bytes (AES-256) — a corrupt or truncated grant should fail loudly
 *  at import time, not produce silent garbage ciphertext later. */
export function decodeCollectionKey(base64Key: string): Uint8Array<ArrayBuffer> {
  const bytes = fromBase64(base64Key)
  if (bytes.length !== 32) {
    throw new Error(`invalid collection key: expected 32 bytes, got ${bytes.length}`)
  }
  return bytes
}
