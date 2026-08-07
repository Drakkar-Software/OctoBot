import type { UserActionConfiguration } from '@drakkar.software/octobot-protocol'

/** One built-but-unsent action inside a proposal. `after: 'previous-confirmed'`
 *  marks an action that must not be appended until the PRIOR entry in the
 *  array has been confirmed by the node — the only case this applies to
 *  today is `automations.create()`'s `strategy_create` → `automation_create`
 *  race (see `orchestration/createAutomation.ts`). A privileged executor
 *  (one that actually has append rights) must honor this ordering; a
 *  read-only proposer never appends anything itself, so it just carries the
 *  constraint as data. */
export type ProposedActionEntry = {
  configuration: UserActionConfiguration
  after?: 'previous-confirmed'
}

/** A batch of built-but-unsent user actions, QR-encodable. Produced by a
 *  read-only-connected client's write methods instead of appending; consumed
 *  by a privileged client (one with real append rights) to actually execute
 *  them after a human reviews and confirms. */
export interface ActionProposal {
  v: 1
  kind: 'octobot-action-proposal'
  actions: ProposedActionEntry[]
  /** Human-readable summary for a confirm screen, when the generic
   *  per-action `configuration.name`/`action_type` derivation isn't enough
   *  (e.g. a multi-action batch). */
  label?: string
  createdAt: string
}

export function encodeActionProposal(actions: ProposedActionEntry[], opts?: { label?: string }): string {
  const proposal: ActionProposal = {
    v: 1,
    kind: 'octobot-action-proposal',
    actions,
    ...(opts?.label ? { label: opts.label } : {}),
    createdAt: new Date().toISOString(),
  }
  return JSON.stringify(proposal)
}

/** Parse and structurally validate a scanned/pasted action-proposal payload.
 *  Throws on anything that isn't shaped like one — callers doing QR
 *  classification should catch and fall through to the next candidate
 *  parser rather than propagate. */
export function decodeActionProposal(payload: string): ActionProposal {
  let parsed: unknown
  try {
    parsed = JSON.parse(payload)
  } catch {
    throw new Error('not valid JSON')
  }
  if (typeof parsed !== 'object' || parsed === null) throw new Error('not an object')
  const p = parsed as Record<string, unknown>
  if (p.v !== 1 || p.kind !== 'octobot-action-proposal') throw new Error('not an action proposal payload')
  if (!Array.isArray(p.actions) || p.actions.length === 0) throw new Error('malformed action proposal: actions')
  for (const entry of p.actions as unknown[]) {
    if (typeof entry !== 'object' || entry === null || !('configuration' in entry)) {
      throw new Error('malformed action proposal: entry')
    }
  }
  if (typeof p.createdAt !== 'string') throw new Error('malformed action proposal: createdAt')
  return p as unknown as ActionProposal
}
