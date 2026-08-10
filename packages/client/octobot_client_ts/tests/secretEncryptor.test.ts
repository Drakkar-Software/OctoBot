import { describe, it, expect } from 'vitest'
import { createSecretEncryptor, createRawKeyEncryptor } from '../src/crypto/secretEncryptor.js'
import { decodeCollectionKey, deriveCollectionKeys } from '../src/crypto/collectionKeys.js'

const SALT = 'octobot-starfish-identity-v1'
const INFO = 'octobot-sync-user-data'

describe('createSecretEncryptor', () => {
  it('round-trips a document through encrypt/decrypt', async () => {
    const enc = createSecretEncryptor('0x' + '11'.repeat(32), SALT, INFO)
    const doc = { hello: 'world', n: 42, nested: { a: [1, 2, 3] } }
    const wrapper = await enc.encrypt(doc)
    expect(wrapper).toHaveProperty('iv')
    expect(wrapper).toHaveProperty('data')
    expect(await enc.decrypt(wrapper)).toEqual(doc)
  })

  it('decrypts a {iv,data} blob given as a JSON string, not just an object', async () => {
    const enc = createSecretEncryptor('0x' + '11'.repeat(32), SALT, INFO)
    const wrapper = await enc.encrypt({ a: 1 })
    expect(await enc.decrypt(JSON.stringify(wrapper) as unknown as Record<string, unknown>)).toEqual({ a: 1 })
  })

  it('resolves to {} instead of crashing on a never-written document, in both real shapes a node sends', async () => {
    // A collection that has never been pushed for this identity pulls back
    // as either the JSON literal `null`, or — per an actual node's own
    // observed behavior — the STRING "null" (same opaque-string convention
    // real blobs use, just carrying the JSON `null` literal instead of a
    // real {iv,data} envelope). Both must resolve to {}, not throw
    // "Cannot read properties of null (reading 'iv')".
    const enc = createSecretEncryptor('0x' + '11'.repeat(32), SALT, INFO)
    expect(await enc.decrypt(null as unknown as Record<string, unknown>)).toEqual({})
    expect(await enc.decrypt('null' as unknown as Record<string, unknown>)).toEqual({})
  })

  it('a "0x"-prefixed secret and its stripped form produce an INTEROPERABLE encryptor (both derive the same key)', async () => {
    const withPrefix = createSecretEncryptor('0x' + 'ab'.repeat(32), SALT, INFO)
    const stripped = createSecretEncryptor('ab'.repeat(32), SALT, INFO)
    const wrapper = await withPrefix.encrypt({ ok: true })
    // If a document encrypted with the prefixed form did not decrypt under
    // the stripped form, this would throw (AES-GCM auth tag mismatch) — this
    // is the exact bug the 0x fix closes: this package's own writes must be
    // decryptable regardless of which form a caller happens to pass in.
    expect(await stripped.decrypt(wrapper)).toEqual({ ok: true })
  })

  it('a genuinely different secret cannot decrypt another secret\'s ciphertext', async () => {
    const a = createSecretEncryptor('0x' + '11'.repeat(32), SALT, INFO)
    const b = createSecretEncryptor('0x' + '22'.repeat(32), SALT, INFO)
    const wrapper = await a.encrypt({ secret: 'value' })
    await expect(b.decrypt(wrapper)).rejects.toThrow()
  })

  it('a different `info` (collection) cannot decrypt another collection\'s ciphertext, same secret', async () => {
    const secret = '0x' + '33'.repeat(32)
    const userData = createSecretEncryptor(secret, SALT, 'octobot-sync-user-data')
    const accounts = createSecretEncryptor(secret, SALT, 'octobot-sync-user-accounts')
    const wrapper = await userData.encrypt({ a: 1 })
    await expect(accounts.decrypt(wrapper)).rejects.toThrow()
  })

  it('two encryptions of the same document produce different ciphertext (random IV)', async () => {
    const enc = createSecretEncryptor('0x' + '11'.repeat(32), SALT, INFO)
    const a = await enc.encrypt({ same: true })
    const b = await enc.encrypt({ same: true })
    expect(a.data).not.toBe(b.data)
    expect(a.iv).not.toBe(b.iv)
  })
})

describe('createRawKeyEncryptor', () => {
  it('round-trips a document through encrypt/decrypt', async () => {
    const keys = deriveCollectionKeys('0x' + '44'.repeat(32), ['userData'])
    const enc = createRawKeyEncryptor(decodeCollectionKey(keys.userData!))
    const doc = { a: 'b', list: [1, 2] }
    const wrapper = await enc.encrypt(doc)
    expect(await enc.decrypt(wrapper)).toEqual(doc)
  })

  it('is interoperable with createSecretEncryptor derived for the same (secret, salt, info)', async () => {
    const secret = '0x' + '55'.repeat(32)
    const viaSecret = createSecretEncryptor(secret, SALT, INFO)
    const keys = deriveCollectionKeys(secret, ['userData'])
    const viaRawKey = createRawKeyEncryptor(decodeCollectionKey(keys.userData!))

    const wrapper = await viaSecret.encrypt({ interop: true })
    expect(await viaRawKey.decrypt(wrapper)).toEqual({ interop: true })
  })

  it('a raw key derived for a different collection cannot decrypt this one\'s ciphertext', async () => {
    const secret = '0x' + '66'.repeat(32)
    const keys = deriveCollectionKeys(secret, ['userData', 'accounts'])
    const userDataEnc = createRawKeyEncryptor(decodeCollectionKey(keys.userData!))
    const accountsEnc = createRawKeyEncryptor(decodeCollectionKey(keys.accounts!))
    const wrapper = await userDataEnc.encrypt({ a: 1 })
    await expect(accountsEnc.decrypt(wrapper)).rejects.toThrow()
  })

  it('rejects a byte length WebCrypto has no AES key size for', async () => {
    // AES-GCM accepts 128/192/256-bit keys, so a 16-byte input is actually
    // valid (AES-128) — WebCrypto's own length check only fires for a size
    // that isn't any of the three. The real 32-byte enforcement for this
    // package's collection keys lives in `decodeCollectionKey`, tested in
    // `collectionKeys.test.ts`; this only checks `createRawKeyEncryptor`
    // doesn't silently accept complete garbage.
    await expect(createRawKeyEncryptor(new Uint8Array(20)).encrypt({ a: 1 })).rejects.toThrow()
  })
})
