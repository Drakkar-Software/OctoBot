import { describe, it, expect } from 'vitest'
import {
  encodeActionProposal,
  decodeActionProposal,
  UnsupportedActionProposalVersionError,
  type ProposedActionEntry,
} from '../src/protocol/proposal.js'
import { buildStopAutomationConfig, buildCreateStrategyConfig, buildCreateAutomationConfig } from '../src/protocol/actions.js'
import { strategy } from '../src/client/strategy.js'

describe('encodeActionProposal / decodeActionProposal', () => {
  it('round-trips a single-action proposal', () => {
    const entries: ProposedActionEntry[] = [{ configuration: buildStopAutomationConfig('auto_1') }]
    const payload = encodeActionProposal(entries, { label: 'Stop automation auto_1' })
    const decoded = decodeActionProposal(payload)
    expect(decoded.v).toBe(1)
    expect(decoded.kind).toBe('octobot-action-proposal')
    expect(decoded.label).toBe('Stop automation auto_1')
    expect(decoded.actions).toHaveLength(1)
    expect(decoded.actions[0].configuration).toEqual(buildStopAutomationConfig('auto_1'))
    expect(decoded.actions[0].after).toBeUndefined()
    expect(decoded.createdAt).toBeTruthy()
  })

  it('round-trips the automations.create two-action ordered case', () => {
    const dca = strategy.dca({ pairs: ['BTC/USDT'], buyOrderAmount: '25' })
    const input = { name: 'My DCA', strategy: dca, accountIds: ['acc_1'] }
    const entries: ProposedActionEntry[] = [
      { configuration: buildCreateStrategyConfig(input.strategy) },
      { configuration: buildCreateAutomationConfig(input), after: 'previous-confirmed' },
    ]
    const decoded = decodeActionProposal(encodeActionProposal(entries))
    expect(decoded.actions).toHaveLength(2)
    expect(decoded.actions[0].after).toBeUndefined()
    expect(decoded.actions[1].after).toBe('previous-confirmed')
    expect((decoded.actions[1].configuration as { action_type?: string }).action_type).toBe('automation_create')
  })

  it('decodeActionProposal rejects garbage and mismatched kinds', () => {
    expect(() => decodeActionProposal('not json')).toThrow()
    expect(() => decodeActionProposal(JSON.stringify({ v: 1, kind: 'something-else' }))).toThrow()
    expect(() => decodeActionProposal(JSON.stringify({ v: 1, kind: 'octobot-action-proposal', actions: [], createdAt: 'x' }))).toThrow()
    expect(() => decodeActionProposal(JSON.stringify({ v: 1, kind: 'octobot-action-proposal', actions: [{}], createdAt: 'x' }))).toThrow()
  })

  it('label is omitted entirely when not provided, not serialized as undefined', () => {
    const payload = encodeActionProposal([{ configuration: buildStopAutomationConfig('a') }])
    expect(JSON.parse(payload)).not.toHaveProperty('label')
  })

  it('rejects a recognised envelope with an unsupported v as a distinguishable error, not a generic parse failure', () => {
    const futurePayload = JSON.stringify({
      v: 2,
      kind: 'octobot-action-proposal',
      actions: [{ configuration: buildStopAutomationConfig('a') }],
      createdAt: new Date().toISOString(),
    })
    expect(() => decodeActionProposal(futurePayload)).toThrow(UnsupportedActionProposalVersionError)
    try {
      decodeActionProposal(futurePayload)
      expect.unreachable()
    } catch (err) {
      expect(err).toBeInstanceOf(UnsupportedActionProposalVersionError)
      expect((err as UnsupportedActionProposalVersionError).version).toBe(2)
    }
  })

  it('a mismatched kind still throws the generic error, not the version error', () => {
    expect(() => decodeActionProposal(JSON.stringify({ v: 2, kind: 'something-else' })))
      .not.toThrow(UnsupportedActionProposalVersionError)
  })
})
