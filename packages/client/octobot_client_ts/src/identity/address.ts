import { secp256k1 } from '@noble/curves/secp256k1.js'
import { keccak_256 } from '@noble/hashes/sha3.js'
import { toHex } from '../internal/bytes.js'

// EIP-55 checksum-casing and EVM address derivation. Previously duplicated
// verbatim across auth/cap-provider.ts and auth/auth-core.ts in
// @drakkar.software/octobot-sdk — consolidated here.

function eip55Address(lower: string): string {
  const hash = toHex(keccak_256(new TextEncoder().encode(lower)))
  return '0x' + Array.from(lower, (c, i) => (parseInt(hash[i], 16) >= 8 ? c.toUpperCase() : c)).join('')
}

/** EIP-55 checksummed EVM address derived from a secp256k1 private key. */
export function deriveEvmAddress(privateKey: Uint8Array): string {
  const pubkey = secp256k1.getPublicKey(privateKey, false) // 65-byte uncompressed
  const hash = keccak_256(pubkey.slice(1))                 // keccak256 of 64-byte (x, y)
  return eip55Address(toHex(hash.slice(12)))               // last 20 bytes → checksummed address
}
