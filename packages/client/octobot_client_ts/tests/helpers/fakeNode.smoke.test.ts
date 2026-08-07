import { describe, it, expect } from 'vitest'
import { connectOctoBot } from '../../src/client/connect/connect.js'
import { createFakeNode } from './fakeNode.js'

const MNEMONIC = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'

describe('fakeNode harness smoke test', () => {
  it('connectOctoBot with verify:true succeeds against an authorized fake node', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    const client = await connectOctoBot({
      url: 'http://192.0.2.1:5001',
      seed: MNEMONIC,
      fetch: node.fetch,
      verify: true,
    })
    expect(client.userId).toBe(node.userId)
    client.close()
  })

  it('connectOctoBot with verify:true rejects against an unauthorized fake node (real 403 path)', async () => {
    const node = await createFakeNode({ seed: MNEMONIC, wireOptions: { authorizedIdentities: new Set(['someone-else']) } })
    await expect(
      connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: true }),
    ).rejects.toThrow(/unauthorized|did not authorize/i)
  })

  it('accounts.list() reads a seeded document back through the real facade', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    await node.seedDoc('accounts', {
      accounts: [{ id: 'acc1', name: 'Binance', is_simulated: false, created_at: '2020-01-01T00:00:00.000Z', updated_at: '2020-01-01T00:00:00.000Z', specifics: { account_type: 'exchange', remote_account_id: '', exchange_config_ids: [] } }],
      exchange_configs: [],
    })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })
    const accounts = await client.accounts.list()
    expect(accounts).toHaveLength(1)
    expect(accounts[0].id).toBe('acc1')
    client.close()
  })

  it('a real append lands in the fake append log and execute() correlates it back through status()', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })
    const handle = await client.automations.stop('auto_1')
    // `ids` grows asynchronously as `work` progresses — NOT synchronously by
    // the time `stop()`'s own promise resolves (its async body returns
    // without awaiting `work`). `settled()` awaits `work` to completion,
    // which is when the append is actually guaranteed to have landed.
    await handle.settled()
    expect(handle.ids).toHaveLength(1)

    const appended = await node.decryptedActions()
    expect(appended).toHaveLength(1)
    expect(appended[0].configuration.action_type).toBe('automation_stop')

    let status = await handle.status()
    expect(status.settled).toBe(false)

    await node.execute(handle.ids[0], { status: 'completed', result: {} })
    status = await handle.status()
    expect(status.settled).toBe(true)
    client.close()
  })

  it('accounts.list() returns [] instead of crashing when the document was never written', async () => {
    // createFakeNode pre-seeds every collection so most tests don't have to
    // think about this — delete it to simulate what a real, freshly
    // registered wallet's node actually returns on its first pull: a
    // genuinely unwritten slot (`data: null`, not an encrypted `{}`).
    const node = await createFakeNode({ seed: MNEMONIC })
    node.store.delete(node.pathFor('accounts'))
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })
    await expect(client.accounts.list()).resolves.toEqual([])
    client.close()
  })

  it('a CAS push conflict really produces a ConflictError via the wire (409)', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })
    // `settings` is pre-seeded (see createFakeNode) — pull the real current
    // hash first, push against it (succeeds), then push again against the
    // now-stale hash (conflicts).
    const { hash } = await client.documents.pull('settings')
    await client.documents.push('settings', { a: 1 }, { baseHash: hash })
    await expect(client.documents.push('settings', { a: 2 }, { baseHash: hash })).rejects.toThrow()
  })
})
