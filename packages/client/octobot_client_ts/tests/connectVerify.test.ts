import { describe, it, expect } from 'vitest'
import { connectOctoBot } from '../src/client/connect/connect.js'
import { OctoBotAuthError, OctoBotError } from '../src/client/core/errors.js'
import { registerDerivationScheme } from '../src/identity/derivationSchemes.js'
import { deriveBip44PrivateKey, isEvmPrivateKey, normalizeEvmPrivateKey } from '../src/identity/evm.js'
import { createFakeNode } from './helpers/fakeNode.js'

const MNEMONIC = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'

let altRegistered = false
function ensureAltScheme() {
  if (altRegistered) return
  registerDerivationScheme({
    id: 'connect-verify-alt',
    derive: async (mnemonicOrKey) => {
      if (isEvmPrivateKey(mnemonicOrKey)) return normalizeEvmPrivateKey(mnemonicOrKey)
      return deriveBip44PrivateKey(mnemonicOrKey.trim().split(/\s+/).reverse().join(' '))
    },
  })
  altRegistered = true
}

describe('verify:true maps a real node 403 to OctoBotAuthError naming what was tried', () => {
  it('an unauthorized identity produces OctoBotAuthError with the real address/userId/derivation', async () => {
    const node = await createFakeNode({ seed: MNEMONIC, wireOptions: { authorizedIdentities: new Set(['someone-else']) } })
    let caught: unknown
    try {
      await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: true })
    } catch (err) {
      caught = err
    }
    expect(caught).toBeInstanceOf(OctoBotAuthError)
    const err = caught as OctoBotAuthError
    expect(err.code).toBe('unauthorized')
    expect(err.userId).toBe(node.userId)
    expect(err.derivation).toBe('bip44')
    expect(err.address).toMatch(/^0x[0-9a-fA-F]{40}$/)
    expect(err.message).toContain(err.address)
  })

  it('a real 500 propagates as code "http", never mistaken for an auth failure', async () => {
    const node = await createFakeNode({
      seed: MNEMONIC,
      wireOptions: { statusFor: (req) => (req.path.includes('/pull/') ? 500 : undefined) },
    })
    let caught: unknown
    try {
      await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: true })
    } catch (err) {
      caught = err
    }
    expect(caught).toBeInstanceOf(OctoBotError)
    expect(caught).not.toBeInstanceOf(OctoBotAuthError)
    expect((caught as OctoBotError).code).toBe('http')
  })

  it('verify:false issues zero fetches even in "auto" mode', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, seedDerivation: 'auto', fetch: node.fetch, verify: false })
    expect(node.requests).toHaveLength(0)
    client.close()
  })

  it('"auto" with a raw private key issues exactly one probe, no matter how many schemes are registered', async () => {
    ensureAltScheme()
    const rawKey = '0x' + 'cd'.repeat(32)
    const node = await createFakeNode({ seed: rawKey })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: rawKey, seedDerivation: 'auto', fetch: node.fetch, verify: true })
    // Every scheme passes a raw key through unchanged, so trying more than
    // one is pointless — auto short-circuits to a single candidate.
    const probes = node.requests.filter((r) => r.path.includes('/pull/') && r.path.includes('/data'))
    expect(probes).toHaveLength(1)
    client.close()
  })

  it('"auto" stops at the first scheme the node authorizes', async () => {
    ensureAltScheme()
    // The fake node is only authorized under the ALT scheme's derived identity.
    const altNode = await createFakeNode({ seed: MNEMONIC, derivation: 'connect-verify-alt' })
    const node = await createFakeNode({
      seed: MNEMONIC,
      wireOptions: { authorizedIdentities: new Set([altNode.userId]) },
    })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, seedDerivation: 'auto', fetch: node.fetch, verify: true })
    expect(client.userId).toBe(altNode.userId)
    client.close()
  })

  it('"auto" with every scheme unauthorized reports the LAST candidate tried', async () => {
    ensureAltScheme()
    const node = await createFakeNode({ seed: MNEMONIC, wireOptions: { authorizedIdentities: new Set(['nobody']) } })
    await expect(
      connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, seedDerivation: 'auto', fetch: node.fetch, verify: true }),
    ).rejects.toThrow(OctoBotAuthError)
  })
})
