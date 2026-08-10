import {
  deriveRootIdentityFromEvmSignature,
  mintDeviceCap,
  scopes,
} from '@drakkar.software/starfish-identities'
import type { RootIdentity } from '@drakkar.software/starfish-identities'
import type { StarfishCapProvider } from '@drakkar.software/starfish-client'
import { secp256k1 } from '@noble/curves/secp256k1.js'
import { keccak_256 } from '@noble/hashes/sha3.js'
import { deriveEvmAddress } from './address.js'
import { hexToBytes } from '../internal/bytes.js'
import { getDerivationScheme, DEFAULT_DERIVATION_SCHEME_ID } from './derivationSchemes.js'

/** Which derivation scheme identifies the wallet — a `DerivationScheme.id`
 *  from `derivationSchemes.ts`. `'bip44'` (the standard `m/44'/60'/0'/0/0`
 *  path) is the only one this package ships, and the default; a consumer
 *  needing another wallet type registers one via `registerDerivationScheme`
 *  and passes its id here. An unknown id throws rather than silently
 *  deriving under the wrong scheme. */
export type KeyDerivation = string

// The EVM wallet signs this challenge (EIP-191 personal_sign) to derive its
// Starfish root identity. Must match octobot_sync/constants.py SYNC_BOOTSTRAP_CHALLENGE.
// @see packages/sync/octobot_sync/constants.py — SYNC_BOOTSTRAP_CHALLENGE
// @remarks Changing this breaks sync silently: the client and node would derive
// different root identities from the same wallet.
export const BOOTSTRAP_CHALLENGE = 'octobot:sync-bootstrap'

/**
 * Sign challenge text with EIP-191 personal_sign.
 * Returns 65-byte r‖s‖v signature where v = recoveryBit + 27.
 * Matches Python web3.Account.sign_message(encode_defunct(text=challenge)).signature.
 */
function signBootstrap(privateKey: Uint8Array, challenge: string): Uint8Array {
  const enc = new TextEncoder()
  const msgBytes = enc.encode(challenge)
  const prefix = enc.encode(`\x19Ethereum Signed Message:\n${msgBytes.length}`)
  const combined = new Uint8Array(prefix.length + msgBytes.length)
  combined.set(prefix, 0)
  combined.set(msgBytes, prefix.length)
  const hash = keccak_256(combined)
  // noble v2: format:'recovered' → recovery_bit(1) ‖ r(32) ‖ s(32)
  const sig = secp256k1.sign(hash, privateKey, { format: 'recovered', lowS: true, prehash: false })
  const out = new Uint8Array(65)
  out.set(sig.slice(1, 33), 0)   // r
  out.set(sig.slice(33, 65), 32) // s
  out[64] = sig[0] + 27          // v (Ethereum: 27/28)
  return out
}

/**
 * Derive the wallet's Starfish root identity (userId + Ed25519/X25519 device
 * keys) from a BIP39 seed. Exported so a caller under the same wallet (e.g. a
 * strategy-marketplace or third-party client) can build a session under the
 * SAME identity as this package's sync stack — one wallet → one Starfish
 * userId across every namespace.
 *
 * `derivation` defaults to `'bip44'` — picking the wrong scheme derives a
 * DIFFERENT identity, which looks exactly like "pairing worked" followed by
 * an empty account (nothing was ever synced under that identity).
 */
export async function deriveRoot(
  seed: string,
  derivation: KeyDerivation = DEFAULT_DERIVATION_SCHEME_ID,
): Promise<RootIdentity> {
  const privateKeyHex = await getDerivationScheme(derivation).derive(seed)
  const privateKey = hexToBytes(privateKeyHex)
  const address = deriveEvmAddress(privateKey)
  const signature = signBootstrap(privateKey, BOOTSTRAP_CHALLENGE)
  return deriveRootIdentityFromEvmSignature({ address, signature, challenge: BOOTSTRAP_CHALLENGE })
}

/**
 * Starfish v3 cap-cert provider derived from a BIP39 mnemonic seed.
 *
 * Mirrors octobot_sync/auth/provider.py WalletCapProvider: the EVM wallet
 * deterministically signs BOOTSTRAP_CHALLENGE (EIP-191), the 65-byte
 * signature is HKDF-expanded into a root Ed25519+X25519 identity, and a
 * fresh short-lived device cap-cert is minted per request.
 *
 * userId = sha256(rootEdPub)[:32] hex — used as the {identity} URL segment
 * instead of the raw EVM address.
 *
 * @see packages/sync/octobot_sync/auth/provider.py — WalletCapProvider
 */
export class WalletCapProvider implements StarfishCapProvider {
  private readonly rootPromise: Promise<RootIdentity>

  constructor(seed: string, derivation: KeyDerivation = DEFAULT_DERIVATION_SCHEME_ID) {
    this.rootPromise = deriveRoot(seed, derivation)
  }

  async getCap() {
    const root = await this.rootPromise
    const cap = await mintDeviceCap(
      root.keys.edPriv,
      root.keys.edPub,
      { edPubHex: root.keys.edPub, kemPubHex: root.keys.kemPub },
      scopes.rootAll(),
    )
    // pubHex omitted: device caps bind the identity via cap.sub, not audience
    return { cap, devEdPrivHex: root.keys.edPriv }
  }

  async getUserId(): Promise<string> {
    return (await this.rootPromise).userId
  }
}
