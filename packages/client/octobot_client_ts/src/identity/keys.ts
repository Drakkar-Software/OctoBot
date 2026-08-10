import { keccak_256 } from '@noble/hashes/sha3.js'
import { deriveEvmAddress } from './address.js'
import { toHex, hexToBytes } from '../internal/bytes.js'
import type { KeyDerivation } from './capProvider.js'
import { getDerivationScheme, DEFAULT_DERIVATION_SCHEME_ID } from './derivationSchemes.js'

/** One session's worth of derived key material, keyed off the seed so a
 *  caller can hold several independently (unlike the module-level singleton
 *  cache octobot-sdk uses internally). */
export type KeyCache = {
  getWalletAddress(seed: string, derivation?: KeyDerivation): Promise<string>
  getEncryptionKey(seed: string, derivation?: KeyDerivation): Promise<string>
  clear(): void
}

type CachedKey = { fingerprint: string; privateKey: Uint8Array; address: string }

function fingerprintOf(seed: string, derivation: KeyDerivation): string {
  return toHex(keccak_256(new TextEncoder().encode(`${derivation}:${seed}`)))
}

/** Creates an isolated single-entry key-derivation cache: avoids re-deriving
 *  PBKDF2 + BIP32 on every call for the same (seed, derivation) pair. Keyed
 *  by a hash of both so the raw seed isn't held as a map key. Each
 *  `connectOctoBot()` session gets its own — this is the ONE piece of state
 *  this package keeps beyond a single call, and it's dropped by
 *  `close()`/`clear()`. */
export function createKeyCache(): KeyCache {
  let cached: CachedKey | null = null

  async function getKey(seed: string, derivation: KeyDerivation): Promise<CachedKey> {
    const fingerprint = fingerprintOf(seed, derivation)
    if (cached?.fingerprint === fingerprint) return cached
    const privateKeyHex = await getDerivationScheme(derivation).derive(seed)
    const privateKey = hexToBytes(privateKeyHex)
    const address = deriveEvmAddress(privateKey)
    cached = { fingerprint, privateKey, address }
    return cached
  }

  return {
    /** EIP-55 checksummed EVM address the seed derives to. `derivation`
     *  defaults to `'bip44'`. */
    getWalletAddress: async (seed, derivation = DEFAULT_DERIVATION_SCHEME_ID) => (await getKey(seed, derivation)).address,
    /** The private key hex used as the HKDF secret for payload encryption
     *  (see crypto/secretEncryptor.ts). `derivation` defaults to `'bip44'`. */
    getEncryptionKey: async (seed, derivation = DEFAULT_DERIVATION_SCHEME_ID) =>
      '0x' + toHex((await getKey(seed, derivation)).privateKey),
    clear: () => { cached = null },
  }
}
