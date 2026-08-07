import { describe, it, expect } from 'vitest'
import { createKeyCache, WalletCapProvider } from '../src/identity/index.js'

// Fixed mnemonic for deterministic key derivation across runs.
const SEED = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'
const SEED_B = 'zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo wrong'

describe('createKeyCache: wallet address derivation', () => {
  it('derives a 0x-prefixed EIP-55 checksummed address', async () => {
    const addr = await createKeyCache().getWalletAddress(SEED)
    expect(addr).toMatch(/^0x[0-9a-fA-F]{40}$/)
  })

  it('is deterministic for the same seed, across independent caches', async () => {
    const a = await createKeyCache().getWalletAddress(SEED)
    const b = await createKeyCache().getWalletAddress(SEED)
    expect(a).toBe(b)
  })

  it('returns different addresses for different seeds', async () => {
    const a = await createKeyCache().getWalletAddress(SEED)
    const b = await createKeyCache().getWalletAddress(SEED + ' xxx')
    expect(a).not.toBe(b)
  })

  it('caches across consecutive calls on the same instance (same seed)', async () => {
    const cache = createKeyCache()
    const a = await cache.getWalletAddress(SEED)
    const b = await cache.getWalletAddress(SEED)
    expect(a).toBe(b)
  })

  it('clear() drops the cache without changing what a later call derives', async () => {
    const cache = createKeyCache()
    const a = await cache.getWalletAddress(SEED)
    cache.clear()
    const b = await cache.getWalletAddress(SEED)
    expect(a).toBe(b)
  })
})

describe('createKeyCache: encryption key derivation', () => {
  it('returns a 0x-prefixed 32-byte hex private key', async () => {
    const key = await createKeyCache().getEncryptionKey(SEED)
    expect(key).toMatch(/^0x[0-9a-f]{64}$/)
  })

  it('is consistent with the address derived from the same seed', async () => {
    const cache = createKeyCache()
    const [addr, key] = await Promise.all([
      cache.getWalletAddress(SEED),
      cache.getEncryptionKey(SEED),
    ])
    expect(addr).toBeTruthy()
    expect(key).toBeTruthy()
    expect(addr.length).toBe(42)
    expect(key.length).toBe(66)
  })
})

describe('auth: WalletCapProvider (cap-cert)', () => {
  it('getUserId returns a 32-char lowercase hex string', async () => {
    const prov = new WalletCapProvider(SEED)
    const userId = await prov.getUserId()
    expect(userId).toMatch(/^[0-9a-f]{32}$/)
  })

  it('getUserId is deterministic for the same seed', async () => {
    const a = await new WalletCapProvider(SEED).getUserId()
    const b = await new WalletCapProvider(SEED).getUserId()
    expect(a).toBe(b)
  })

  it('getUserId differs for different seeds', async () => {
    const a = await new WalletCapProvider(SEED).getUserId()
    const b = await new WalletCapProvider(SEED_B).getUserId()
    expect(a).not.toBe(b)
  })

  it('getCap returns a device cap with devEdPrivHex', async () => {
    const prov = new WalletCapProvider(SEED)
    const { cap, devEdPrivHex } = await prov.getCap()
    expect(devEdPrivHex).toMatch(/^[0-9a-f]{64}$/)
    expect(cap.kind).toBe('device')
    expect(cap.v).toBe(1)
    expect(cap.sig).toBeTruthy()
  })

  it('getCap emits no pubHex (device cap uses cap.sub for identity)', async () => {
    const prov = new WalletCapProvider(SEED)
    const result = await prov.getCap()
    expect('pubHex' in result).toBe(false)
  })
})
