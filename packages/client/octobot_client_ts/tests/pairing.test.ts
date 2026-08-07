import { describe, it, expect } from 'vitest'
import { createReadOnlyPairing, parseReadOnlyPairing } from '../src/identity/pairing.js'
import { deriveRoot } from '../src/identity/capProvider.js'
import { fromBase64 } from '../src/internal/bytes.js'

const MNEMONIC = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'
const NODE = { host: '192.0.2.1', port: 5001 }

describe('createReadOnlyPairing / parseReadOnlyPairing', () => {
  it('round-trips through JSON, and parse validates the shape', async () => {
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE)
    const parsed = parseReadOnlyPairing(payload)
    expect(parsed.v).toBe(2)
    expect(parsed.kind).toBe('octobot-read-only-pairing')
    expect(parsed.node).toEqual(NODE)
    expect(parsed.userId).toMatch(/^[0-9a-f]{32}$/)
    expect(parsed.device.edPriv).toMatch(/^[0-9a-f]+$/)
    expect(parsed.cap.sig).toBeTruthy()
  })

  it('carries per-collection subkeys, one per granted collection, never the wallet secret', async () => {
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE)
    const parsed = parseReadOnlyPairing(payload)
    expect(Object.keys(parsed.collectionKeys).sort()).toEqual(['accounts', 'userData'])
    expect(parsed).not.toHaveProperty('encryptionSecret')
    for (const key of Object.values(parsed.collectionKeys)) {
      expect(typeof key).toBe('string')
      // 32-byte AES-256 key, base64-encoded.
      expect(fromBase64(key!).length).toBe(32)
    }
    // Not the raw wallet key: the leaked v1 secret was always `0x`-prefixed
    // 64-hex; a base64-encoded 32-byte key never parses as that.
    expect(parsed.collectionKeys.userData).not.toMatch(/^0x[0-9a-f]{64}$/)
  })

  it('the two collection subkeys are different from each other', async () => {
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE)
    const parsed = parseReadOnlyPairing(payload)
    expect(parsed.collectionKeys.userData).not.toBe(parsed.collectionKeys.accounts)
  })

  it('no field in the payload lets a holder reconstruct the wallet root identity', async () => {
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE)
    const parsed = parseReadOnlyPairing(payload)
    // Every string field in the payload, run through deriveRoot (the exact
    // reconstruction a v1 leak allowed), must NOT reproduce rootEdPub —
    // deriveRoot succeeds on any 64-hex string, so "does it throw" alone
    // would be a vacuous check; it must actually fail to reproduce the root.
    const candidates: string[] = [
      parsed.device.edPriv, parsed.device.kemPriv,
      ...Object.values(parsed.collectionKeys).filter((v): v is string => typeof v === 'string'),
    ]
    for (const candidate of candidates) {
      const attempt = await deriveRoot(candidate, 'bip44').catch(() => null)
      if (attempt) expect(attempt.keys.edPub).not.toBe(parsed.rootEdPub)
    }
  })

  it('defaults the scope to read+list only on userData and accounts', async () => {
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE)
    const parsed = parseReadOnlyPairing(payload)
    expect(parsed.scope.ops).toEqual(['read', 'list'])
    expect(parsed.scope.ops).not.toContain('write')
    expect(parsed.scope.collections).toEqual(['userData', 'accounts'])
  })

  it('accepts a caller-supplied collection subset, still never write', async () => {
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE, { collections: ['settings'] })
    const parsed = parseReadOnlyPairing(payload)
    expect(parsed.scope.collections).toEqual(['settings'])
    expect(parsed.scope.ops).toEqual(['read', 'list'])
    expect(Object.keys(parsed.collectionKeys)).toEqual(['settings'])
  })

  it('rejects an unknown collection name rather than silently minting a useless grant', async () => {
    await expect(createReadOnlyPairing(MNEMONIC, 'bip44', NODE, { collections: ['not-a-real-collection'] }))
      .rejects.toThrow(/unknown collection/)
  })

  it('an empty collections array grants nothing decryptable', async () => {
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE, { collections: [] })
    const parsed = parseReadOnlyPairing(payload)
    expect(parsed.collectionKeys).toEqual({})
  })

  it('the minted cap is bound to the ephemeral device pubkey, not the root', async () => {
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE)
    const parsed = parseReadOnlyPairing(payload)
    expect(parsed.cap.sub).toBe(parsed.device.edPub)
    expect(parsed.cap.sub).not.toBe(parsed.rootEdPub)
    expect(parsed.cap.iss).toBe(parsed.rootEdPub)
  })

  it('two mints from the same seed produce two independent device identities but identical collection keys', async () => {
    const a = parseReadOnlyPairing((await createReadOnlyPairing(MNEMONIC, 'bip44', NODE)).payload)
    const b = parseReadOnlyPairing((await createReadOnlyPairing(MNEMONIC, 'bip44', NODE)).payload)
    expect(a.device.edPub).not.toBe(b.device.edPub)
    expect(a.rootEdPub).toBe(b.rootEdPub) // same wallet
    // The collection key is a pure function of (secret, salt, info) — it
    // does not depend on the ephemeral device identity, so two independent
    // mints for the same wallet grant the same decryption key. This is
    // expected (both grants decrypt the same node documents), not a bug.
    expect(a.collectionKeys.userData).toBe(b.collectionKeys.userData)
  })

  it('parseReadOnlyPairing rejects garbage, mismatched kinds, and the deprecated v1 shape', () => {
    expect(() => parseReadOnlyPairing('not json')).toThrow()
    expect(() => parseReadOnlyPairing(JSON.stringify({ v: 2, kind: 'something-else' }))).toThrow()
    expect(() => parseReadOnlyPairing(JSON.stringify({ v: 1, kind: 'octobot-read-only-pairing' }))).toThrow()
    expect(() => parseReadOnlyPairing(JSON.stringify({ v: 2, kind: 'octobot-read-only-pairing' }))).toThrow()
  })

  it('parseReadOnlyPairing rejects a payload missing collectionKeys', () => {
    const { host, port } = NODE
    const bad = {
      v: 2, kind: 'octobot-read-only-pairing',
      node: { host, port }, rootEdPub: 'a'.repeat(64), userId: 'b'.repeat(32),
      device: { edPriv: 'c'.repeat(64), edPub: 'd'.repeat(64), kemPriv: 'e'.repeat(64), kemPub: 'f'.repeat(64) },
      cap: { v: 1, sig: 'sig' },
      scope: { ops: ['read', 'list'], collections: ['userData'] },
    }
    expect(() => parseReadOnlyPairing(JSON.stringify(bad))).toThrow(/collectionKeys/)
  })
})
