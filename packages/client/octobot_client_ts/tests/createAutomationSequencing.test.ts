import { describe, it, expect } from 'vitest'
import type { UserAction, UserActionConfiguration } from '@drakkar.software/octobot-protocol'
import {
  runCreateAutomation,
  AutomationActionFailedError,
  AutomationTimeoutError,
  type ActionEmitter,
} from '../src/protocol/orchestration/createAutomation.js'
import { strategy } from '../src/client/strategy.js'

const dca = strategy.dca({ pairs: ['BTC/USDT'], buyOrderAmount: '25' })
const INPUT = { name: 'My DCA', strategy: dca, accountIds: ['acc1'] }

/** A scriptable `ActionEmitter`: `emit` records every call and assigns an
 *  incrementing id; `poll` returns whatever the test has configured for the
 *  action ids emitted so far. Both are pure, in-memory — no fake node
 *  needed, matching this module's own I/O-free layering rule. */
function stubEmitter() {
  const emitted: { id: string; configuration: UserActionConfiguration }[] = []
  const statusById = new Map<string, UserAction['status']>()
  const resultById = new Map<string, Record<string, unknown>>()
  let counter = 0

  const io: ActionEmitter = {
    emit: async (configuration) => {
      const id = `ua_${++counter}`
      emitted.push({ id, configuration })
      statusById.set(id, 'pending')
      return id
    },
    poll: async () =>
      emitted.map(({ id, configuration }) => ({
        id,
        status: statusById.get(id) ?? 'pending',
        configuration,
        ...(resultById.has(id) ? { result: resultById.get(id) } : {}),
      })) as UserAction[],
  }
  return { io, emitted, setStatus: (id: string, s: UserAction['status'], result?: Record<string, unknown>) => {
    statusById.set(id, s)
    if (result !== undefined) resultById.set(id, result)
  } }
}

describe('automation_create is not appended until strategy_create is confirmed completed', () => {
  it('emit is called exactly once, for strategy_create, while the strategy action is pending/running', async () => {
    const { io, emitted, setStatus } = stubEmitter()
    const promise = runCreateAutomation(io, INPUT, { pollDelay: () => 0 })

    // Let the first phase actually emit before we start asserting.
    await new Promise((r) => setTimeout(r, 5))
    expect(emitted).toHaveLength(1)
    expect(emitted[0].configuration.action_type).toBe('strategy_create')

    // Advance through pending -> running without confirming: still only one emit.
    setStatus(emitted[0].id, 'running')
    await new Promise((r) => setTimeout(r, 5))
    expect(emitted).toHaveLength(1)

    // Confirm the strategy phase: NOW automation_create should be emitted.
    setStatus(emitted[0].id, 'completed', {})
    await new Promise((r) => setTimeout(r, 5))
    expect(emitted).toHaveLength(2)
    expect(emitted[1].configuration.action_type).toBe('automation_create')

    // Complete the automation phase too so the overall promise resolves.
    setStatus(emitted[1].id, 'completed', {})
    const { automationId } = await promise
    expect(automationId).toBeNull() // stub result carries no created_automation_id
  })

  it('a strategy-phase failure never emits automation_create at all', async () => {
    const { io, emitted, setStatus } = stubEmitter()
    const promise = runCreateAutomation(io, INPUT, { pollDelay: () => 0 })
    await new Promise((r) => setTimeout(r, 5))
    setStatus(emitted[0].id, 'failed', { error_message: 'strategy_not_found' })
    await expect(promise).rejects.toThrow(AutomationActionFailedError)
    expect(emitted).toHaveLength(1) // never reached the automation phase
  })
})

describe('a failed or unconfirmed phase surfaces the typed error the docs tell callers to branch on', () => {
  it('a failed strategy phase rejects AutomationActionFailedError with phase "strategy" and the real detail', async () => {
    const { io, emitted, setStatus } = stubEmitter()
    const promise = runCreateAutomation(io, INPUT, { pollDelay: () => 0 })
    await new Promise((r) => setTimeout(r, 5))
    setStatus(emitted[0].id, 'failed', { error_message: 'strategy_not_found' })
    let caught: unknown
    try {
      await promise
    } catch (err) {
      caught = err
    }
    expect(caught).toBeInstanceOf(AutomationActionFailedError)
    const err = caught as AutomationActionFailedError
    expect(err.phase).toBe('strategy')
    expect(err.detail).toBe('strategy_not_found')
  })

  it('a failed automation phase rejects with phase "automation"', async () => {
    const { io, emitted, setStatus } = stubEmitter()
    const promise = runCreateAutomation(io, INPUT, { pollDelay: () => 0 })
    await new Promise((r) => setTimeout(r, 5))
    setStatus(emitted[0].id, 'completed', {})
    await new Promise((r) => setTimeout(r, 5))
    expect(emitted).toHaveLength(2)
    setStatus(emitted[1].id, 'failed', { error_message: 'invalid_account' })
    let caught: unknown
    try {
      await promise
    } catch (err) {
      caught = err
    }
    expect(caught).toBeInstanceOf(AutomationActionFailedError)
    expect((caught as AutomationActionFailedError).phase).toBe('automation')
    expect((caught as AutomationActionFailedError).detail).toBe('invalid_account')
  })

  it('an unconfirmed phase times out as AutomationTimeoutError naming the stuck phase', async () => {
    const { io } = stubEmitter() // never advances any status
    await expect(runCreateAutomation(io, INPUT, { pollDelay: () => 0, timeoutMs: 20 })).rejects.toMatchObject({
      name: 'AutomationTimeoutError',
      phase: 'strategy',
    })
  })

  it('the deadline is computed once, not reset per phase: a slow strategy phase leaves little budget for automation', async () => {
    const { io, emitted, setStatus } = stubEmitter()
    const promise = runCreateAutomation(io, INPUT, { pollDelay: () => 15, timeoutMs: 40 })
    // Let the strategy phase burn through most of the 40ms budget before confirming.
    await new Promise((r) => setTimeout(r, 30))
    setStatus(emitted[0]?.id ?? 'never', 'completed', {})
    await expect(promise).rejects.toMatchObject({ name: 'AutomationTimeoutError', phase: 'automation' })
  })

  it('an already-aborted signal rejects with an unwrapped AbortError DOMException', async () => {
    const { io } = stubEmitter()
    const controller = new AbortController()
    controller.abort()
    let caught: unknown
    try {
      await runCreateAutomation(io, INPUT, { pollDelay: () => 0, signal: controller.signal })
    } catch (err) {
      caught = err
    }
    expect(caught).toBeInstanceOf(DOMException)
    expect((caught as DOMException).name).toBe('AbortError')
  })
})
