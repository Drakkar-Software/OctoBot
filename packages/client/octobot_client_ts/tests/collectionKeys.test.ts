import { describe, it, expect } from 'vitest'
import { deriveCollectionKeys, decodeCollectionKey } from '../src/crypto/collectionKeys.js'
import { NODE_COLLECTIONS, type NodeCollectionKey } from '../src/collections/nodeCollections.js'
import { toBase64 } from '../src/internal/bytes.js'

const SECRET = '0x' + '11'.repeat(32)
const ALL_COLLECTIONS = Object.keys(NODE_COLLECTIONS) as NodeCollectionKey[]

describe('deriveCollectionKeys', () => {
  it('derives one base64 32-byte key per requested collection', () => {
    const keys = deriveCollectionKeys(SECRET, ['userData', 'accounts'])
    expect(Object.keys(keys).sort()).toEqual(['accounts', 'userData'])
    for (const value of Object.values(keys)) {
      expect(decodeCollectionKey(value!).length).toBe(32)
    }
  })

  it('is deterministic: the same secret + collection always derives the same key', () => {
    const a = deriveCollectionKeys(SECRET, ['userData'])
    const b = deriveCollectionKeys(SECRET, ['userData'])
    expect(a.userData).toBe(b.userData)
  })

  it('every collection derives a different key from every other collection', () => {
    const keys = deriveCollectionKeys(SECRET, ALL_COLLECTIONS)
    const values = Object.values(keys)
    expect(new Set(values).size).toBe(values.length)
  })

  it('a different secret derives a completely different key', () => {
    const other = '0x' + '22'.repeat(32)
    const a = deriveCollectionKeys(SECRET, ['userData'])
    const b = deriveCollectionKeys(other, ['userData'])
    expect(a.userData).not.toBe(b.userData)
  })

  it('strips a leading 0x before deriving, matching the node — with vs without the prefix are different secrets otherwise', () => {
    const withPrefix = deriveCollectionKeys('0xabc123', ['userData'])
    const stripped = deriveCollectionKeys('abc123', ['userData'])
    expect(withPrefix.userData).toBe(stripped.userData)
  })

  it('returns an empty object for an empty collection list', () => {
    expect(deriveCollectionKeys(SECRET, [])).toEqual({})
  })

  it('derives a key for every known node collection without throwing', () => {
    const keys = deriveCollectionKeys(SECRET, ALL_COLLECTIONS)
    expect(Object.keys(keys)).toHaveLength(ALL_COLLECTIONS.length)
  })

  it('is one-way: the derived key bytes never equal the secret in any encoding', () => {
    const keys = deriveCollectionKeys(SECRET, ['userData'])
    const bytes = decodeCollectionKey(keys.userData!)
    expect(toBase64(bytes)).not.toBe(SECRET)
    expect(Buffer.from(bytes).toString('hex')).not.toContain(SECRET.replace('0x', ''))
  })
})

describe('decodeCollectionKey', () => {
  it('round-trips through deriveCollectionKeys', () => {
    const keys = deriveCollectionKeys(SECRET, ['accounts'])
    const bytes = decodeCollectionKey(keys.accounts!)
    expect(bytes).toBeInstanceOf(Uint8Array)
    expect(bytes.length).toBe(32)
  })

  it('throws on a base64 string that does not decode to 32 bytes', () => {
    expect(() => decodeCollectionKey(toBase64(new Uint8Array(16)))).toThrow(/32 bytes/)
    expect(() => decodeCollectionKey(toBase64(new Uint8Array(48)))).toThrow(/32 bytes/)
  })

  it('throws on malformed base64', () => {
    expect(() => decodeCollectionKey('not base64!!!')).toThrow()
  })
})
