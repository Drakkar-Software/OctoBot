import { describe, it, expect } from 'vitest'
import { connectOctoBot } from '../src/client/connect/connect.js'
import { createFakeNode } from './helpers/fakeNode.js'

const MNEMONIC = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'

// `actionHandle.ts`'s own doc comment says settled() "resolves once the
// node reports every phase completed." In practice, only automations.create()
// actually polls for that (via runCreateAutomation). Every other facade's
// `work` promise is a single immediate re-pull/list right after appending —
// against a node that has processed nothing, that re-pull just returns
// whatever was already there, and settled() resolves anyway. This test pins
// the REAL, weaker contract as it exists today so a caller reading these
// docs isn't the one who discovers the gap in production.
describe('settled() resolves without the node confirming anything, for every facade except automations.create', () => {
  it('accounts.create(): settled() resolves (to null) even though the node never executed the append', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })
    const handle = await client.accounts.create({ name: 'New', type: 'exchange', exchange: 'binance', credentials: { apiKey: 'k', apiSecret: 's' } })
    const result = await handle.settled()
    expect(result).toBeNull() // the account was never actually created node-side
    // Confirm the node genuinely never executed anything for this handle.
    const status = await handle.status()
    expect(status.actions).toHaveLength(0) // nothing in userData.user_actions yet
    client.close()
  })

  it('accounts.refresh(): settled() resolves to the PRE-refresh balances, not anything the node computed', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    await node.seedDoc('accounts', {
      accounts: [{ id: 'acc1', name: 'Binance', is_simulated: false, created_at: '2020-01-01T00:00:00.000Z', updated_at: '2020-01-01T00:00:00.000Z', specifics: { account_type: 'exchange', remote_account_id: '', exchange_config_ids: [] } }],
      exchange_configs: [],
    })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })
    const handle = await client.accounts.refresh(['acc1'])
    const result = await handle.settled()
    expect(result).toHaveLength(1) // the stale pre-refresh list, not a node-confirmed one
    client.close()
  })

  it('automations.update(): settled() resolves without the node ever seeing the edit take effect', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })
    const dca = (await import('../src/client/strategy.js')).strategy.dca({ pairs: ['BTC/USDT'], buyOrderAmount: '25' })
    const handle = await client.automations.update('auto1', { name: 'Renamed', strategy: dca, accountIds: ['acc1'] })
    const result = await handle.settled()
    expect(result).toBeNull() // the node was never told, so get() finds nothing
    client.close()
  })

  it('automations.stop(): settled() resolves with no confirmation the node ever stopped anything', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })
    const handle = await client.automations.stop('auto1')
    await expect(handle.settled()).resolves.toBeUndefined() // resolves regardless
    const status = await handle.status()
    expect(status.actions).toHaveLength(0)
    client.close()
  })

  it('a failed action for the emitted id in userData does NOT make settled() reject, for a non-automations.create facade', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })
    const handle = await client.automations.stop('auto1')
    // settled() already resolved above without polling — even if the node
    // goes on to mark the action failed afterward, THIS handle's settled()
    // promise is memoized to its original (already-resolved) outcome.
    await handle.settled()
    await node.execute(handle.ids[0], { status: 'failed', result: { error_message: 'not_found' } })
    await expect(handle.settled()).resolves.toBeUndefined() // memoized — does not re-check and reject
  })
})
