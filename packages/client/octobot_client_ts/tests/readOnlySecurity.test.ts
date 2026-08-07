import { describe, it, expect } from 'vitest'
import { connectReadOnlyDevice } from '../src/client/connect/readOnly.js'
import { createReadOnlyPairing, parseReadOnlyPairing } from '../src/identity/pairing.js'
import { OctoBotScopeError } from '../src/client/core/errors.js'
import { strategy } from '../src/client/strategy.js'
import { createFakeNode } from './helpers/fakeNode.js'

const MNEMONIC = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'
const NODE = { host: '192.0.2.1', port: 5001 }

describe('a read-only client issues zero writes when every write method is called', () => {
  it('accounts/automations/strategies write methods never send a non-GET request', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE)
    const client = await connectReadOnlyDevice(payload, { fetch: node.fetch })

    const dca = strategy.dca({ pairs: ['BTC/USDT'], buyOrderAmount: '25' })
    const proposals = [
      await client.accounts.create({ name: 'New', type: 'exchange', exchange: 'binance', credentials: { apiKey: 'k', apiSecret: 's' } }),
      await client.accounts.update('acc1', { name: 'Renamed', type: 'exchange', exchange: 'binance', credentials: { apiKey: 'k', apiSecret: 's' } }),
      await client.accounts.delete('acc1'),
      await client.accounts.refresh(['acc1']),
      await client.automations.create({ name: 'My DCA', strategy: dca, accountIds: ['acc1'] }),
      await client.automations.update('auto1', { name: 'My DCA', strategy: dca, accountIds: ['acc1'] }),
      await client.automations.stop('auto1'),
      await client.strategies.create(dca),
      await client.strategies.update(dca),
      await client.strategies.delete(dca.id),
    ]

    // Every write method returns a ProposedAction instead of performing a
    // write: a QR-encodable proposal a privileged (append-capable) device
    // scans and executes after a human confirms — never an in-place
    // success/failure on this session. Asserting the shape here, not just
    // the absence of network writes below, is the point: an `await` that
    // resolves proves these calls don't throw OR silently no-op, they
    // produce a real, inspectable proposal every time.
    for (const proposed of proposals) {
      expect(proposed.actions.length).toBeGreaterThan(0)
      expect(proposed.payload).toBeDefined()
      expect(typeof proposed.payload).toBe('string')
      expect(proposed.payload.length).toBeGreaterThan(0)
    }

    const nonGet = node.requests.filter((r) => r.method !== 'GET')
    expect(nonGet).toHaveLength(0)
    const actionsRequests = node.requests.filter((r) => r.path.includes('/actions'))
    expect(actionsRequests).toHaveLength(0)
    client.close()
  })
})

describe('the scope gate fires before any fetch, and a forged/widened scope cannot bypass it', () => {
  it('an ungranted collection throws OctoBotScopeError before any network request', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE, { collections: ['accounts'] })
    const client = await connectReadOnlyDevice(payload, { fetch: node.fetch })

    await expect(client.documents.pull('settings')).rejects.toThrow(OctoBotScopeError)
    await expect(client.automations.list()).rejects.toThrow(OctoBotScopeError) // pulls userData, outside this grant
    await expect(client.strategies.list()).rejects.toThrow(OctoBotScopeError)
    expect(node.requests).toHaveLength(0)
    client.close()
  })

  it('rewriting scope.ops/scope.collections to claim broader access does not widen what the client actually does', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE, { collections: ['accounts'] })
    const parsed = parseReadOnlyPairing(payload) as unknown as {
      scope: { ops: string[]; collections: string[] }
      collectionKeys: Record<string, string>
    }
    // Forge a payload claiming write access to every collection, while
    // leaving collectionKeys untouched (a forger has no way to mint new
    // ones — they're one-way HKDF derivations of the wallet secret this
    // read-only session never has).
    parsed.scope = { ops: ['read', 'list', 'write'], collections: ['userData', 'accounts', 'settings', 'strategies', 'actions', 'accountTrading'] }
    const forged = JSON.stringify(parsed)

    const client = await connectReadOnlyDevice(forged, { fetch: node.fetch })
    // Still gated by collectionKeys alone — the forged scope changed nothing.
    await expect(client.documents.pull('settings')).rejects.toThrow(OctoBotScopeError)
    const proposed = await client.accounts.create({ name: 'X', type: 'generic' })
    expect(proposed.payload).toBeDefined() // still a proposal, never an append
    expect(node.requests.filter((r) => r.method !== 'GET')).toHaveLength(0)
    client.close()
  })
})
