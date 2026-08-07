import { describe, it, expect } from 'vitest'
import { createSession, createReadOnlySession, type SessionCapProvider } from '../src/client/core/session.js'
import { OctoBotScopeError } from '../src/client/core/errors.js'
import { deriveCollectionKeys } from '../src/crypto/collectionKeys.js'

const MNEMONIC = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'
const NODE = { host: '192.0.2.1', port: 5001 }
const UNREACHABLE_FETCH = (() => Promise.reject(new Error('no network in this test'))) as unknown as typeof fetch

describe('createSession (full wallet)', () => {
  it('collectionEncryptor resolves for any node collection — a full session is never scope-limited', async () => {
    const session = createSession({
      origin: 'http://192.0.2.1:5001', node: NODE, address: '0xabc', userId: 'user1',
      derivation: 'bip44', seed: MNEMONIC, fetch: UNREACHABLE_FETCH, defaultTimeoutMs: 1000,
    })
    for (const collection of ['userData', 'accounts', 'settings', 'strategies', 'actions', 'accountTrading'] as const) {
      await expect(session.collectionEncryptor(collection)).resolves.toBeDefined()
    }
    session.close()
  })

  it('walletAddress() resolves to the derived address', async () => {
    const session = createSession({
      origin: 'http://192.0.2.1:5001', node: NODE, address: '0xabc', userId: 'user1',
      derivation: 'bip44', seed: MNEMONIC, fetch: UNREACHABLE_FETCH, defaultTimeoutMs: 1000,
    })
    await expect(session.walletAddress()).resolves.toMatch(/^0x[0-9a-fA-F]{40}$/)
    session.close()
  })

  it('close() does not throw and is idempotent', () => {
    const session = createSession({
      origin: 'http://192.0.2.1:5001', node: NODE, address: '0xabc', userId: 'user1',
      derivation: 'bip44', seed: MNEMONIC, fetch: UNREACHABLE_FETCH, defaultTimeoutMs: 1000,
    })
    expect(() => { session.close(); session.close() }).not.toThrow()
  })
})

describe('createReadOnlySession', () => {
  function fakeCapProvider(): SessionCapProvider {
    return {
      getCap: async () => { throw new Error('not exercised in this test') },
      getUserId: async () => 'user1',
    }
  }

  it('collectionEncryptor resolves only for a granted collection', async () => {
    const collectionKeys = deriveCollectionKeys('0x' + '11'.repeat(32), ['userData', 'accounts'])
    const session = createReadOnlySession({
      origin: 'http://192.0.2.1:5001', node: NODE, userId: 'user1',
      fetch: UNREACHABLE_FETCH, defaultTimeoutMs: 1000, capProvider: fakeCapProvider(), collectionKeys,
    })
    await expect(session.collectionEncryptor('userData')).resolves.toBeDefined()
    await expect(session.collectionEncryptor('accounts')).resolves.toBeDefined()
    await expect(session.collectionEncryptor('settings')).rejects.toThrow(OctoBotScopeError)
    await expect(session.collectionEncryptor('strategies')).rejects.toThrow(OctoBotScopeError)
    await expect(session.collectionEncryptor('actions')).rejects.toThrow(OctoBotScopeError)
    await expect(session.collectionEncryptor('accountTrading')).rejects.toThrow(OctoBotScopeError)
  })

  it('an empty grant rejects every collection', async () => {
    const session = createReadOnlySession({
      origin: 'http://192.0.2.1:5001', node: NODE, userId: 'user1',
      fetch: UNREACHABLE_FETCH, defaultTimeoutMs: 1000, capProvider: fakeCapProvider(), collectionKeys: {},
    })
    await expect(session.collectionEncryptor('userData')).rejects.toThrow(OctoBotScopeError)
  })

  it('OctoBotScopeError names the collection it rejected', async () => {
    const session = createReadOnlySession({
      origin: 'http://192.0.2.1:5001', node: NODE, userId: 'user1',
      fetch: UNREACHABLE_FETCH, defaultTimeoutMs: 1000, capProvider: fakeCapProvider(), collectionKeys: {},
    })
    try {
      await session.collectionEncryptor('settings')
      expect.unreachable('should have thrown')
    } catch (err) {
      expect(err).toBeInstanceOf(OctoBotScopeError)
      expect((err as OctoBotScopeError).collection).toBe('settings')
      expect((err as OctoBotScopeError).code).toBe('forbidden_collection')
    }
  })

  it('a granted collection\'s encryptor actually decrypts what a matching createSecretEncryptor produced', async () => {
    const secret = '0x' + '22'.repeat(32)
    const collectionKeys = deriveCollectionKeys(secret, ['userData'])
    const session = createReadOnlySession({
      origin: 'http://192.0.2.1:5001', node: NODE, userId: 'user1',
      fetch: UNREACHABLE_FETCH, defaultTimeoutMs: 1000, capProvider: fakeCapProvider(), collectionKeys,
    })
    const { createSecretEncryptor } = await import('../src/crypto/secretEncryptor.js')
    const { STARFISH_ENCRYPTION_SALT } = await import('../src/crypto/wireConstants.js')
    const writer = createSecretEncryptor(secret, STARFISH_ENCRYPTION_SALT, 'octobot-sync-user-data')
    const wrapper = await writer.encrypt({ hello: 'world' })

    const readerEncryptor = await session.collectionEncryptor('userData')
    expect(await readerEncryptor.decrypt(wrapper)).toEqual({ hello: 'world' })
  })

  it('close() is a no-op and does not throw — there is no derived-key cache on this path', () => {
    const session = createReadOnlySession({
      origin: 'http://192.0.2.1:5001', node: NODE, userId: 'user1',
      fetch: UNREACHABLE_FETCH, defaultTimeoutMs: 1000, capProvider: fakeCapProvider(), collectionKeys: {},
    })
    expect(() => session.close()).not.toThrow()
  })

  it('has no seed/derivation/keyCache/walletAddress on its shape', () => {
    const session = createReadOnlySession({
      origin: 'http://192.0.2.1:5001', node: NODE, userId: 'user1',
      fetch: UNREACHABLE_FETCH, defaultTimeoutMs: 1000, capProvider: fakeCapProvider(), collectionKeys: {},
    })
    expect('seed' in session).toBe(false)
    expect('derivation' in session).toBe(false)
    expect('keyCache' in session).toBe(false)
    expect('walletAddress' in session).toBe(false)
  })
})
