import { describe, it, expect } from 'vitest'
import { connectOctoBot } from '../src/client/connect/connect.js'
import { connectReadOnlyDevice } from '../src/client/connect/readOnly.js'
import { createReadOnlyPairing } from '../src/identity/pairing.js'
import { strategy } from '../src/client/strategy.js'
import { decodeActionProposal } from '../src/protocol/proposal.js'
import { createFakeNode } from './helpers/fakeNode.js'

const MNEMONIC = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'
const NODE = { host: '192.0.2.1', port: 5001 }

describe('automations.update() emits strategy_edit before automation_edit and forwards the caller\'s version verbatim', () => {
  it('the append path: real order, replace-by-id, version unchanged (no auto-bump)', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })

    const edited = strategy.dca({ pairs: ['BTC/USDT'], buyOrderAmount: '50' }, { id: 's_1', version: '1.0.1' })
    const handle = await client.automations.update('auto_1', { name: 'Renamed', strategy: edited, accountIds: ['acc1'] })
    await handle.settled()

    const appended = await node.decryptedActions()
    expect(appended.map((a) => a.configuration.action_type)).toEqual(['strategy_edit', 'automation_edit'])

    const strategyEdit = appended[0].configuration as { id: string; configuration: { version: string } }
    expect(strategyEdit.id).toBe('s_1') // replace-by-id: the strategy's own id, not the automation id
    expect(strategyEdit.configuration.version).toBe('1.0.1') // forwarded verbatim — update() does not bump it

    const automationEdit = appended[1].configuration as { id: string; configuration: { strategy: { id: string; version: string; emit_signals: boolean } } }
    expect(automationEdit.id).toBe('auto_1')
    expect(automationEdit.configuration.strategy).toEqual({ id: 's_1', version: '1.0.1', emit_signals: false })
    client.close()
  })

  it('a same-version strategy_edit is a silent no-op replace, by design — update() performs no version comparison at all', async () => {
    const node = await createFakeNode({ seed: MNEMONIC })
    const client = await connectOctoBot({ url: 'http://192.0.2.1:5001', seed: MNEMONIC, fetch: node.fetch, verify: false })
    const unchanged = strategy.dca({ pairs: ['BTC/USDT'], buyOrderAmount: '25' }, { id: 's_1', version: '1.0.0' })
    const handle = await client.automations.update('auto_1', { name: 'Same', strategy: unchanged, accountIds: ['acc1'] })
    await handle.settled()
    const appended = await node.decryptedActions()
    const strategyEdit = appended[0].configuration as { configuration: { version: string } }
    expect(strategyEdit.configuration.version).toBe('1.0.0') // identical to before — update() never bumps
    client.close()
  })
})

describe('the two read-only write methods no other test touches: accounts.refresh and automations.update proposals', () => {
  it('accounts.refresh() proposes exactly one accounts_refresh action, never appending', async () => {
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE)
    const client = await connectReadOnlyDevice(payload)
    const proposed = await client.accounts.refresh(['acc1'])
    const decoded = decodeActionProposal(proposed.payload)
    expect(decoded.actions).toHaveLength(1)
    expect((decoded.actions[0].configuration as { action_type: string }).action_type).toBe('accounts_refresh')
    client.close()
  })

  it('automations.update() proposes strategy_edit + automation_edit, never appending, with automation_edit chained after strategy_edit', async () => {
    const { payload } = await createReadOnlyPairing(MNEMONIC, 'bip44', NODE)
    const client = await connectReadOnlyDevice(payload)
    const dca = strategy.dca({ pairs: ['BTC/USDT'], buyOrderAmount: '25' })
    const proposed = await client.automations.update('auto_1', { name: 'X', strategy: dca, accountIds: ['acc1'] })
    const decoded = decodeActionProposal(proposed.payload)
    expect(decoded.actions.map((a) => (a.configuration as { action_type: string }).action_type)).toEqual(['strategy_edit', 'automation_edit'])
    // automation_edit resolves the strategy by (id, version) against the node's
    // StrategyProvider, which only the confirmed strategy_edit fills — an
    // executor must not append automation_edit until strategy_edit lands.
    expect(decoded.actions[0].after).toBeUndefined()
    expect(decoded.actions[1].after).toBe('previous-confirmed')
    client.close()
  })
})
