import { describe, it, expect } from 'vitest'
import { createReadOnlyPairing } from '../src/identity/pairing.js'
import { createKeyCache } from '../src/identity/keys.js'

const MNEMONIC = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'
const NODE = { host: '192.0.2.1', port: 5001 }

/** Recursively collect every leaf string value in a parsed JSON structure. */
function leafStrings(value: unknown, out: string[] = []): string[] {
  if (typeof value === 'string') {
    out.push(value)
  } else if (Array.isArray(value)) {
    for (const v of value) leafStrings(v, out)
  } else if (value && typeof value === 'object') {
    for (const v of Object.values(value)) leafStrings(v, out)
  }
  return out
}

describe('no field of a serialized read-only pairing payload contains the wallet secret', () => {
  it('walks every leaf string of the payload and asserts none contain the secret, the mnemonic, or a long run of its hex', async () => {
    const secret = await createKeyCache().getEncryptionKey(MNEMONIC, 'bip44') // '0x' + privkey hex — the actual HKDF secret
    const secretNoPrefix = secret.slice(2)

    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE)
    expect(payload).not.toContain(secret)
    expect(payload).not.toContain(secretNoPrefix)
    expect(payload).not.toContain(MNEMONIC)

    // Any 8+ char contiguous run of the private-key hex would be a strong
    // leak signal — check a sliding window, not just full-string containment.
    for (let i = 0; i + 8 <= secretNoPrefix.length; i += 4) {
      const chunk = secretNoPrefix.slice(i, i + 8)
      expect(payload).not.toContain(chunk)
    }

    const parsed = JSON.parse(payload)
    const leaves = leafStrings(parsed)
    for (const leaf of leaves) {
      expect(leaf).not.toBe(secret)
      expect(leaf).not.toBe(secretNoPrefix)
      expect(leaf.toLowerCase()).not.toContain(secretNoPrefix.toLowerCase())
    }
  })

  it('the same check holds for a payload minted from a raw private key (no mnemonic to derive from)', async () => {
    const rawKey = '0x' + 'ab'.repeat(32)
    const { payload } = await createReadOnlyPairing(rawKey, 'bip44', NODE)
    const parsed = JSON.parse(payload)
    for (const leaf of leafStrings(parsed)) {
      expect(leaf.toLowerCase()).not.toContain('ab'.repeat(32))
    }
  })
})
