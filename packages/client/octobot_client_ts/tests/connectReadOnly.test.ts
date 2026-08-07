import { describe, it, expect } from 'vitest'
import { connectReadOnlyDevice } from '../src/client/connect/readOnly.js'
import { createReadOnlyPairing } from '../src/identity/pairing.js'
import { OctoBotConfigError, OctoBotScopeError } from '../src/client/core/errors.js'

const MNEMONIC = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'
const NODE = { host: '192.0.2.1', port: 5001 } // TEST-NET-1, guaranteed unreachable

describe('connectReadOnlyDevice', () => {
  it('rejects a malformed payload with OctoBotConfigError', async () => {
    await expect(connectReadOnlyDevice('not a real payload')).rejects.toThrow(OctoBotConfigError)
  })

  it('rejects an empty string with OctoBotConfigError', async () => {
    await expect(connectReadOnlyDevice('')).rejects.toThrow(OctoBotConfigError)
  })

  it('rejects a well-formed but different JSON shape (e.g. an action proposal) with OctoBotConfigError', async () => {
    const proposal = JSON.stringify({ v: 1, kind: 'octobot-action-proposal', actions: [], createdAt: '2020-01-01' })
    await expect(connectReadOnlyDevice(proposal)).rejects.toThrow(OctoBotConfigError)
  })

  it('builds a client from a valid pairing payload with no network I/O', async () => {
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE)
    const client = await connectReadOnlyDevice(payload)
    expect(client.url).toBe('http://192.0.2.1:5001')
    expect(client.userId).toMatch(/^[0-9a-f]{32}$/)
    expect(client.accounts).toBeDefined()
    expect(client.automations).toBeDefined()
    expect(client.strategies).toBeDefined()
    expect(client.documents).toBeDefined()
    expect('settings' in client).toBe(false)
    expect('node' in client).toBe(false)
    client.close()
  })

  it('a client built from a narrowed grant throws OctoBotScopeError reaching outside it, before any network I/O', async () => {
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE, { collections: ['accounts'] })
    const client = await connectReadOnlyDevice(payload)
    // automations/strategies both pull userData, which this grant excludes.
    await expect(client.automations.list()).rejects.toThrow(OctoBotScopeError)
    await expect(client.strategies.list()).rejects.toThrow(OctoBotScopeError)
    client.close()
  })
})
