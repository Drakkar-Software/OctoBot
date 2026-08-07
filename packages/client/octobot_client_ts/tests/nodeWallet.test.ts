import { describe, expect, it } from 'vitest'
import {
  nodeWalletFromExport,
  nodeWalletFromSecret,
  nodeWalletKey,
} from '../src/node-api/wallet.js'

// Hardhat's default mnemonic. Its BIP44 account #0 key is widely published, so
// asserting it literally pins this to the value a node would actually sign with
// rather than to whatever the app happens to compute.
const SEED = 'test test test test test test test test test test test junk'
const SEED_KEY = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'
const KEY = '0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318'

describe('nodeWalletFromSecret', () => {
  it('derives a phrase the BIP44 way and keeps the phrase as the backup', async () => {
    expect(await nodeWalletFromSecret(SEED)).toEqual({
      seed: SEED,
      keySource: 'mnemonic',
      derivation: 'bip44',
      key: SEED_KEY,
    })
  })

  it('normalises whitespace and case in a phrase before deriving', async () => {
    const messy = `  TEST   test\ntest ${SEED.split(' ').slice(3).join(' ')}  `
    const imported = await nodeWalletFromSecret(messy)
    expect(imported?.seed).toBe(SEED)
    expect(imported?.key).toBe(SEED_KEY)
  })

  it('takes a 0x private key as the wallet itself, with nothing to derive', async () => {
    expect(await nodeWalletFromSecret(KEY)).toEqual({
      seed: KEY,
      keySource: 'privateKey',
      derivation: 'legacy',
    })
  })

  it('returns null for a secret that is neither a key nor a valid phrase', async () => {
    expect(await nodeWalletFromSecret('0xdeadbeef')).toBeNull()
    expect(await nodeWalletFromSecret(SEED.replace('junk', 'zoo'))).toBeNull()
    expect(await nodeWalletFromSecret('hunter2')).toBeNull()
    expect(await nodeWalletFromSecret('')).toBeNull()
  })
})

describe('nodeWalletFromExport', () => {
  const BARE = KEY.slice(2)
  const SEED_BARE = SEED_KEY.slice(2)

  it('keeps the export mnemonic as the backup when it derives to the export key', async () => {
    expect(await nodeWalletFromExport({ address: '0xabc', private_key: SEED_BARE, seed: SEED }))
      .toEqual({ seed: SEED, keySource: 'mnemonic', derivation: 'bip44', key: SEED_KEY })
  })

  it('falls back to a key-only wallet when the node has no mnemonic', async () => {
    const keyOnly = { seed: KEY, keySource: 'privateKey', derivation: 'legacy' }
    expect(await nodeWalletFromExport({ address: '0xabc', private_key: BARE })).toEqual(keyOnly)
    expect(await nodeWalletFromExport({ address: '0xabc', private_key: BARE, seed: null }))
      .toEqual(keyOnly)
  })

  it('drops a mnemonic that does not derive to the export key', async () => {
    // The node builds both halves from one wallet, so they should always agree.
    // If they ever do not, the key wins — it is what the node signs with — and
    // the phrase is discarded rather than offered as a backup that would restore
    // a different account somewhere else.
    expect(await nodeWalletFromExport({ address: '0xabc', private_key: BARE, seed: SEED }))
      .toEqual({ seed: KEY, keySource: 'privateKey', derivation: 'legacy' })
  })

  it('drops a mnemonic that is not a valid phrase at all', async () => {
    expect(await nodeWalletFromExport({ address: '0xabc', private_key: BARE, seed: 'not a phrase' }))
      .toEqual({ seed: KEY, keySource: 'privateKey', derivation: 'legacy' })
  })

  it('returns null when the export carries no usable key', async () => {
    expect(await nodeWalletFromExport({ address: '0xabc', private_key: '' })).toBeNull()
    expect(await nodeWalletFromExport({ address: '0xabc', private_key: 'nonsense', seed: SEED }))
      .toBeNull()
  })

  it('0x-prefixes and lowercases the key, which the node stores bare', async () => {
    const imported = await nodeWalletFromExport({
      address: '0xabc',
      private_key: BARE.toUpperCase(),
    })
    expect(imported?.seed).toBe(KEY)
  })
})

describe('nodeWalletKey', () => {
  it('prefers the derived key over the phrase', async () => {
    const fromPhrase = await nodeWalletFromSecret(SEED)
    expect(nodeWalletKey(fromPhrase!)).toBe(SEED_KEY)
  })

  it('falls back to the seed when there is no separate key', async () => {
    const fromKey = await nodeWalletFromSecret(KEY)
    expect(nodeWalletKey(fromKey!)).toBe(KEY)
  })
})
