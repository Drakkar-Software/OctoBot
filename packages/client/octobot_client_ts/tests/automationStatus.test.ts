import { describe, it, expect } from 'vitest'
import { workflowStatusToAutomationStatus } from '../src/protocol/state.js'
import { automationViewOf } from '../src/client/core/views.js'
import type { AutomationState } from '@drakkar.software/octobot-protocol'

// Every WorkflowStatus member, plus the two degradation cases.
const CASES: [string | undefined, 'live' | 'draft' | 'stopped'][] = [
  ['scheduled', 'live'],
  ['periodic', 'live'],
  ['running', 'live'],
  ['pending', 'draft'],
  ['canceled', 'stopped'],
  ['failed', 'stopped'],
  ['completed', 'stopped'],
  ['paused-future-value', 'stopped'], // unknown future enum value
  [undefined, 'stopped'],
]

describe('a canceled, failed, or completed workflow never renders as a live bot', () => {
  it.each(CASES)('workflowStatusToAutomationStatus(%s) -> %s', (input, expected) => {
    expect(workflowStatusToAutomationStatus(input)).toBe(expected)
  })

  it('the same default-to-stopped guard holds end to end through automationViewOf, not just the bare mapper', () => {
    const state = {
      id: 'auto1',
      status: 'canceled',
      metadata: { name: 'Dead bot' },
      exchange_account_ids: ['acc1'],
    } as unknown as AutomationState
    const view = automationViewOf(state, [])
    expect(view.status).toBe('stopped')
  })

  it('a genuinely live workflow renders live through automationViewOf', () => {
    const state = {
      id: 'auto1',
      status: 'running',
      metadata: { name: 'Live bot' },
      exchange_account_ids: ['acc1'],
    } as unknown as AutomationState
    expect(automationViewOf(state, []).status).toBe('live')
  })
})
