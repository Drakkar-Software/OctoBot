import { sha256 } from '@noble/hashes/sha2.js'
import { hkdf } from '@noble/hashes/hkdf.js'
import { utf8ToBytes } from '@noble/hashes/utils.js'

/**
 * Derive a raw 32-byte AES-256 key via HKDF-SHA256 over UTF-8(secret) with
 * UTF-8(salt) / UTF-8(info) — the same algorithm `@drakkar.software/
 * starfish-protocol`'s `deriveAesKeyBytes` uses (verified byte-for-byte
 * identical against its WebCrypto implementation for a fixed vector).
 *
 * Reimplemented locally because `deriveAesKeyBytes` is not reachable from
 * that package's public entry point: only `deriveKey`, `IV_BYTES`,
 * `ENCRYPTED_KEY` are re-exported from `./crypto.js`, and there is no
 * `./crypto` subpath in its `exports` map. `@noble/hashes` is already a
 * direct dependency of this package.
 */
export function deriveAesKeyBytes(secret: string, salt: string, info: string): Uint8Array {
  return hkdf(sha256, utf8ToBytes(secret), utf8ToBytes(salt), utf8ToBytes(info), 32)
}
