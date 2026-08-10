import { describe, it, expect } from 'vitest'
import { connectOctoBot } from '../src/client/connect/connect.js'
import { createActionHandle } from '../src/client/adapters/actionHandle.js'
import { createSession } from '../src/client/core/session.js'
import { createFakeNode, type FakeNode } from './helpers/fakeNode.js'

const MNEMONIC = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'

/** A genuine `WalletClientSession` (satisfies `ClientSession`) pointed at a
 *  fake node — same primitive `connectOctoBot` itself uses, so
 *  `createActionHandle` gets a real session, not a hand-rolled stand-in
 *  that only looks like one. */
function realSessionAgainst(node: FakeNode) {
  return createSession({
    origin: 'http://192.0.2.1:5001',
    node: { host: '192.0.2.1', port: 5001 },
    address: '',
    userId: node.userId,
    derivation: 'bip44',
    seed: MNEMONIC,
    fetch: node.fetch,
    defaultTimeoutMs: 5000,
  })
}

describe('an appended action reaches the node as a real append carrying the pending envelope', () => {
  it('accounts.create() lands three real appends with the expected envelope shape', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })

    const handle = await client.accounts.create({ name: 'New', type: 'exchange', exchange: 'binance', credentials: { apiKey: 'k', apiSecret: 's' } })
    await handle.settled()

    const appended = await node.decryptedActions()
    expect(appended).toHaveLength(3)
    for (const a of appended) {
      expect(a.id).toMatch(/^ua_/)
      expect(a.status).toBe('pending')
      expect(typeof a.created_at).toBe('string')
      expect(a.configuration).toBeDefined()
    }
    // Pairwise distinct ids, and they equal handle.ids in append order.
    expect(new Set(appended.map((a) => a.id)).size).toBe(3)
    expect(handle.ids).toEqual(appended.map((a) => a.id))

    // The wire-level append request itself: POST to a path ending in
    // /actions, body carrying NO baseHash key (append, not CAS push).
    const appendRequests = node.requests.filter((r) => r.method === 'POST' && r.path.includes('/actions'))
    expect(appendRequests.length).toBeGreaterThanOrEqual(3)
    for (const r of appendRequests) {
      const body = JSON.parse(r.body ?? '{}')
      expect('baseHash' in body).toBe(false)
      expect(body.data).toBeDefined()
    }

    // Two consecutive appends both land with no conflict.
    const handle2 = await client.automations.stop('auto_1')
    await handle2.settled()
    expect((await node.decryptedActions())).toHaveLength(4)
    client.close()
  })
})

describe('status() does not report settled:true on a handle whose actions have not been appended yet', () => {
  it('an empty-ids handle reports settled:false, not vacuously true', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })

    let resolveWork!: () => void
    const deferred = new Promise<void>((resolve) => {
      resolveWork = resolve
    })
    const handle = createActionHandle(realSessionAgainst(node), [], deferred)
    const status = await handle.status()
    expect(status.settled).toBe(false)
    expect(status.actions).toEqual([])
    resolveWork()
    client.close()
  })

  it('status() correlates ids to node-reported actions, dropping foreign ones, and reports settled only once ALL ids are terminal', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })

    const h1 = await client.automations.stop('auto_1')
    await h1.settled()
    const h2 = await client.automations.stop('auto_2')
    await h2.settled()
    const ids = [...h1.ids, ...h2.ids]

    await node.execute(ids[0], { status: 'completed', result: {} })
    await node.execute(ids[1], { status: 'failed', result: { error_message: 'nope' } })

    const combinedHandle = createActionHandle(realSessionAgainst(node), ids, Promise.resolve())
    let status = await combinedHandle.status()
    expect(status.settled).toBe(true) // completed AND failed are both terminal
    expect(status.actions.map((a) => a.id).sort()).toEqual([...ids].sort())

    // Flip one back to running: no longer settled.
    await node.execute(ids[1], { status: 'running' })
    status = await combinedHandle.status()
    expect(status.settled).toBe(false)
    client.close()
  })
})

describe('accounts.delete() only proposes companion deletes for companions that actually exist', () => {
  it('deleting an exchange account emits all three deletes', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    await node.seedDoc('accounts', {
      accounts: [{
        id: 'acc1', name: 'Binance', is_simulated: false,
        created_at: '2020-01-01T00:00:00.000Z', updated_at: '2020-01-01T00:00:00.000Z',
        authentication_id: 'auth_acc1',
        specifics: { account_type: 'exchange', remote_account_id: '', exchange_config_ids: ['cfg_acc1'] },
      }],
      exchange_configs: [],
    })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })
    const handle = await client.accounts.delete('acc1')
    await handle.settled()
    const appended = await node.decryptedActions()
    expect(appended.map((a) => a.configuration.action_type)).toEqual(['account_delete', 'account_auth_delete', 'exchange_config_delete'])
    client.close()
  })

  it('deleting a generic account (no auth, no exchange config) emits ONLY account_delete', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    await node.seedDoc('accounts', {
      accounts: [{
        id: 'acc2', name: 'Manual', is_simulated: false,
        created_at: '2020-01-01T00:00:00.000Z', updated_at: '2020-01-01T00:00:00.000Z',
        specifics: { account_type: 'generic' },
      }],
      exchange_configs: [],
    })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })
    const handle = await client.accounts.delete('acc2')
    await handle.settled()
    const appended = await node.decryptedActions()
    expect(appended.map((a) => a.configuration.action_type)).toEqual(['account_delete'])
    client.close()
  })

  it('deleting a wallet account (auth, no exchange config) emits account_delete + account_auth_delete only', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    await node.seedDoc('accounts', {
      accounts: [{
        id: 'acc3', name: 'My Wallet', is_simulated: false,
        created_at: '2020-01-01T00:00:00.000Z', updated_at: '2020-01-01T00:00:00.000Z',
        authentication_id: 'auth_acc3',
        specifics: { account_type: 'generic' },
      }],
      exchange_configs: [],
    })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })
    const handle = await client.accounts.delete('acc3')
    await handle.settled()
    const appended = await node.decryptedActions()
    expect(appended.map((a) => a.configuration.action_type)).toEqual(['account_delete', 'account_auth_delete'])
    client.close()
  })

  it('REGRESSION: a transient failure pulling the existing account falls back to deleting ALL companions, never silently orphans them', async () => {
    const node = await createFakeNode({
      seed: MNEMONIC,
      wireOptions: { statusFor: (req) => (req.method === 'GET' && req.path.includes('/accounts') ? 500 : undefined) },
    })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })
    const handle = await client.accounts.delete('acc_unknown')
    await handle.settled()
    const appended = await node.decryptedActions()
    // Can't tell what companions exist (the pull that would tell us failed) —
    // must fall back to the safe old behavior, not "delete nothing".
    expect(appended.map((a) => a.configuration.action_type)).toEqual(['account_delete', 'account_auth_delete', 'exchange_config_delete'])
    client.close()
  })

  it('REGRESSION: a blockchain-kind account carrying exchange_config_ids still gets exchange_config_delete (not gated on account_type === exchange)', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    await node.seedDoc('accounts', {
      accounts: [{
        id: 'acc4', name: 'Chain', is_simulated: false,
        created_at: '2020-01-01T00:00:00.000Z', updated_at: '2020-01-01T00:00:00.000Z',
        specifics: { account_type: 'blockchain', blockchain: 'ethereum', exchange_config_ids: ['cfg_acc4'] },
      }],
      exchange_configs: [],
    })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })
    const handle = await client.accounts.delete('acc4')
    await handle.settled()
    const appended = await node.decryptedActions()
    expect(appended.map((a) => a.configuration.action_type)).toEqual(['account_delete', 'exchange_config_delete'])
    client.close()
  })
})
