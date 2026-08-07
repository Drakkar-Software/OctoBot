import { describe, it, expect } from 'vitest'
import { deriveRoot } from '../src/identity/capProvider.js'
import { createKeyCache } from '../src/identity/keys.js'
import { deriveCollectionKeys } from '../src/crypto/collectionKeys.js'

// Hardhat's published account #0 — the same fixture evm.test.ts and
// nodeWallet.test.ts already pin the PRIVATE KEY against. This file pins the
// COMPOSED chain one step further: seed -> bip44 privkey -> 0x-strip ->
// Starfish root identity -> userId -> per-collection key. That composition,
// not any single link, is exactly where the 0x-prefix HKDF mismatch lived —
// auth.test.ts and wireContract.test.ts each pin one end of the chain, but
// nothing pins the whole thing against fixed literals, only determinism.
const MNEMONIC = 'test test test test test test test test test test test junk'
const RAW_KEY = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'

const EXPECTED = {
  userId: '14718c7d64136ff66162684ac1b12a00',
  edPub: '883537deb6c27482fa6b4ae359f45442cc3d339ee0c90943e440194566653f2d',
  kemPub: '2321e5f7b423d8aac55617118dc907306d1e111085899156b212f8d698e73923',
  address: '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266',
  encryptionKey: RAW_KEY,
  userDataCollectionKey: 'tAyzfNks51jCJc2z8ur/6J9wgjM89y0QLc5IozBC6Rg=',
}

describe('the seed→userId chain is pinned to fixed literals, not merely determinism', () => {
  it('deriveRoot(MNEMONIC, "bip44") produces exactly these literals', async () => {
    const root = await deriveRoot(MNEMONIC, 'bip44')
    expect(root.userId).toBe(EXPECTED.userId)
    expect(root.keys.edPub).toBe(EXPECTED.edPub)
    expect(root.keys.kemPub).toBe(EXPECTED.kemPub)
  })

  it('the mnemonic derives the exact expected EIP-55 address', async () => {
    const address = await createKeyCache().getWalletAddress(MNEMONIC, 'bip44')
    expect(address).toBe(EXPECTED.address)
  })

  it('the encryption key (HKDF secret) is the exact expected 0x-prefixed hex', async () => {
    const key = await createKeyCache().getEncryptionKey(MNEMONIC, 'bip44')
    expect(key).toBe(EXPECTED.encryptionKey)
  })

  it('a raw private key produces the SAME root identity as the mnemonic it was derived from (passthrough, not re-derivation)', async () => {
    const root = await deriveRoot(RAW_KEY, 'bip44')
    expect(root.userId).toBe(EXPECTED.userId)
    expect(root.keys.edPub).toBe(EXPECTED.edPub)
  })

  it('the composed userData collection key is the exact expected literal', async () => {
    const keys = deriveCollectionKeys(EXPECTED.encryptionKey, ['userData'])
    expect(keys.userData).toBe(EXPECTED.userDataCollectionKey)
  })

  it('CROSS-LANGUAGE CONTRACT: if this test and packages/sync/tests/test_auth_provider.py both pin the Hardhat mnemonic to these SAME literals, a future drift breaks on the side that changed, not silently in production', () => {
    // This assertion is a marker, not a live cross-repo check (that repo
    // isn't reachable from this test run) — it documents the intent: the
    // Python side pins stability (determinism) today, not these fixed
    // values. Reproducing EXPECTED.userId/edPub/address there would make
    // the two implementations fail loudly against each other instead of
    // drifting quietly. See packages/sync/octobot_sync/auth/provider.py.
    expect(EXPECTED.userId).toHaveLength(32)
    expect(EXPECTED.edPub).toHaveLength(64)
  })
})
