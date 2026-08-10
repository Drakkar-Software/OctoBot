import { deriveKey } from '@drakkar.software/starfish-protocol'
import type { Encryptor } from '@drakkar.software/starfish-protocol'
import { toBase64, fromBase64 } from '../internal/bytes.js'

// Envelope keys — must match octobot_sync/constants.py BLOB_IV_KEY / BLOB_DATA_KEY.
const BLOB_IV_KEY = 'iv'
const BLOB_DATA_KEY = 'data'
// 96-bit IV for AES-256-GCM — matches Python's IV_BYTES = 12.
const IV_BYTES = 12

/** The node stores wallet private keys with the `0x` prefix stripped
 *  (`community_wallet.py`: `private_key=private_key.removeprefix("0x")`) and
 *  HKDFs that stripped string directly (`octobot_sync/crypto.py`). HKDF
 *  treats its secret as an opaque byte string, not parsed hex, so `"0x1234"`
 *  and `"1234"` derive completely different keys despite representing the
 *  same private key numerically. Every caller here must agree with the node
 *  on the stripped form, so normalize once, centrally, rather than trusting
 *  each call site to strip before calling in. */
function normalizeSecret(secret: string): string {
  return secret.startsWith('0x') ? secret.slice(2) : secret
}

/** Build an `Encryptor` from an already-resolved (or resolving) AES-256-GCM
 *  `CryptoKey`. Shared by `createSecretEncryptor` (derives the key from a
 *  wallet secret) and `createRawKeyEncryptor` (imports an already-derived
 *  key directly — the read-only pairing path, where the payload carries a
 *  precomputed per-collection subkey rather than the wallet secret itself). */
function buildAesGcmEncryptor(keyPromise: Promise<CryptoKey>): Encryptor {
  return {
    async encrypt(data: Record<string, unknown>): Promise<Record<string, unknown>> {
      const key = await keyPromise
      const ivBuf = new ArrayBuffer(IV_BYTES)
      globalThis.crypto.getRandomValues(new Uint8Array(ivBuf))
      const iv = new Uint8Array(ivBuf)
      const plaintext = new TextEncoder().encode(JSON.stringify(data))
      const ciphertext = new Uint8Array(
        await globalThis.crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, plaintext),
      )
      return {
        [BLOB_IV_KEY]: toBase64(iv),
        [BLOB_DATA_KEY]: toBase64(ciphertext),
      }
    },

    async decrypt(wrapper: Record<string, unknown>): Promise<Record<string, unknown>> {
      // Server wraps the {iv,data} blob as a JSON string inside StoredDocument.data.
      // Parse it when needed so both current (string) and future (object) server formats work.
      const blob: Record<string, unknown> | null =
        typeof wrapper === 'string'
          ? (JSON.parse(wrapper) as Record<string, unknown> | null)
          : (wrapper as Record<string, unknown> | null)
      // A collection that has never been pushed for this identity pulls back
      // as the STRING "null" (the same opaque-string convention every real
      // blob uses, just carrying the JSON literal `null` instead of a real
      // {iv,data} envelope) — parsing it above yields the JS value `null`,
      // not an object. Nothing to decrypt yet.
      if (blob == null) return {}
      const key = await keyPromise
      const iv = fromBase64(blob[BLOB_IV_KEY] as string)
      const ciphertext = fromBase64(blob[BLOB_DATA_KEY] as string)
      const plaintext = new Uint8Array(
        await globalThis.crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ciphertext),
      )
      return JSON.parse(new TextDecoder().decode(plaintext)) as Record<string, unknown>
    },
  }
}

/**
 * Build a symmetric Encryptor keyed by HKDF-SHA256(secret, salt, info) → AES-256-GCM.
 *
 * Mirrors octobot_sync/crypto.py SecretEncryptor. The {iv, data} envelope is
 * compatible with Python's encrypt_bytes_to_blob_dict / decrypt_blob_dict_to_bytes.
 *
 * The key is derived once and cached in the returned Encryptor instance.
 */
export function createSecretEncryptor(
  secret: string,
  salt: string,
  info: string,
): Encryptor {
  return buildAesGcmEncryptor(deriveKey(normalizeSecret(secret), salt, info))
}

/**
 * Build an Encryptor from an already-derived raw AES-256 key (32 bytes),
 * imported as a non-extractable AES-GCM `CryptoKey` — no HKDF step. Used for
 * the read-only pairing path, where the payload carries a precomputed
 * per-collection subkey (see `crypto/collectionKeys.ts`) instead of the
 * wallet secret, so the recipient can decrypt exactly the granted
 * collections and nothing else, and can never re-derive any other key.
 */
export function createRawKeyEncryptor(keyBytes: Uint8Array<ArrayBuffer>): Encryptor {
  const keyPromise = globalThis.crypto.subtle.importKey(
    'raw',
    keyBytes,
    { name: 'AES-GCM' },
    false,
    ['encrypt', 'decrypt'],
  )
  return buildAesGcmEncryptor(keyPromise)
}
