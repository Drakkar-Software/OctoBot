import type { UserAction, UserActionConfiguration } from '@drakkar.software/octobot-protocol'
import { buildCreateStrategyConfig, buildCreateAutomationConfig, type AutomationBuildInput } from '../actions.js'
import { actionErrorDetails, createdAutomationIdOf } from '../state.js'
import { sleep, pollDelay } from '../poll.js'

/** What `runCreateAutomation` needs from its caller: a way to push one action
 *  onto the node's queue, and a way to learn the node's current view of
 *  every queued action (draining any outbox first, if the caller has one).
 *  `connectOctoBot()`'s facade wires this to a direct append + pull;
 *  `octobot-sdk`'s offline engine wires it to its outbox + CRDT store — same
 *  state machine, two very different delivery mechanisms underneath. */
export type ActionEmitter = {
  /** Emit one action's wire configuration. Returns its (client-assigned) id. */
  emit: (configuration: UserActionConfiguration) => Promise<string>
  /** Deliver anything not yet sent, then return the node's current view of
   *  every user action (from the latest `user-data` pull). Called once per
   *  poll tick. */
  poll: () => Promise<UserAction[]>
}

export type CreateAutomationInput = AutomationBuildInput

export type CreateAutomationProgress = { phase: 'strategy' | 'automation'; done: boolean }

export type CreateAutomationOptions = {
  /** Total budget across BOTH phases. Default 60_000. */
  timeoutMs?: number
  /** Default: the node's own confirmed cadence, min(2000 + n*1500, 8000). */
  pollDelay?: (attempt: number) => number
  signal?: AbortSignal
  onProgress?: (p: CreateAutomationProgress) => void
}

/** A specific action the node executed and rejected. Not retriable by
 *  resubmitting the same configuration unchanged. */
export class AutomationActionFailedError extends Error {
  readonly phase: 'strategy' | 'automation'
  readonly detail: string | null
  constructor(phase: 'strategy' | 'automation', detail: string | null) {
    super(`${phase} action failed${detail ? `: ${detail}` : ''}`)
    this.name = 'AutomationActionFailedError'
    this.phase = phase
    this.detail = detail
  }
}

/** Neither phase failed outright — the node just never confirmed within the
 *  budget. Worth a fresh `runCreateAutomation` call, not a resubmit. */
export class AutomationTimeoutError extends Error {
  readonly phase: 'strategy' | 'automation'
  constructor(phase: 'strategy' | 'automation') {
    super(`${phase} action not confirmed within the timeout budget`)
    this.name = 'AutomationTimeoutError'
    this.phase = phase
  }
}

/**
 * Two-phase sequenced automation creation: emits `strategy_create`, polls the
 * node until it confirms, then emits `automation_create` and polls until the
 * node reports a result.
 *
 * This eliminates a concurrent-execution race: the node executes queued
 * actions concurrently, and `automation_create` resolves its strategy by
 * (id, version) — if it ran before `strategy_create` registered that
 * strategy in the node's StrategyProvider, it would fail non-retriably with
 * `strategy_not_found`. Sequencing guarantees the strategy exists first.
 *
 * Callers enforcing an account's automation cap (a product policy the node
 * itself does not know about) must check it BEFORE calling this — it is not
 * part of the protocol and this function does not re-derive it.
 */
export async function runCreateAutomation(
  io: ActionEmitter,
  input: CreateAutomationInput,
  opts: CreateAutomationOptions = {},
): Promise<{ automationId: string | null }> {
  const { timeoutMs = 60_000, pollDelay: nextDelay = pollDelay, signal, onProgress } = opts
  const deadline = Date.now() + timeoutMs

  async function runPhase(phase: 'strategy' | 'automation', configuration: UserActionConfiguration): Promise<UserAction> {
    onProgress?.({ phase, done: false })
    const actionId = await io.emit(configuration)

    for (let attempt = 0; ; attempt++) {
      if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
      if (Date.now() >= deadline) throw new AutomationTimeoutError(phase)
      await sleep(nextDelay(attempt))
      if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
      if (Date.now() >= deadline) throw new AutomationTimeoutError(phase)

      const actions = await io.poll()
      const action = actions.find((a) => a.id === actionId)

      if (action?.status === 'failed') throw new AutomationActionFailedError(phase, actionErrorDetails(action))
      if (action?.status === 'completed') {
        onProgress?.({ phase, done: true })
        return action
      }
    }
  }

  await runPhase('strategy', buildCreateStrategyConfig(input.strategy))
  const autoAction = await runPhase('automation', buildCreateAutomationConfig(input))
  return { automationId: createdAutomationIdOf(autoAction) }
}
