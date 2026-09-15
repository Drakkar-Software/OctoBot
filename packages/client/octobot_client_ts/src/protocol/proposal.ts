import type { ActionProposal, ProposedActionEntry } from '@drakkar.software/octobot-protocol'

export type { ActionProposal, ProposedActionEntry }

const SUPPORTED_VERSION = 1

/** A payload that parsed as JSON, looked like an action-proposal envelope by
 *  `kind`, but carries a `v` this build does not understand. Distinct from
 *  the generic "not an action proposal payload" error so a caller can tell a
 *  scanned proposal from a future app apart from a corrupt or unrelated scan
 *  and prompt the user to update instead. */
export class UnsupportedActionProposalVersionError extends Error {
  constructor(public readonly version: unknown) {
    super(`unsupported action proposal version: ${JSON.stringify(version)}`)
    this.name = 'UnsupportedActionProposalVersionError'
  }
}

export function encodeActionProposal(actions: ProposedActionEntry[], opts?: { label?: string }): string {
  const proposal: ActionProposal = {
    v: SUPPORTED_VERSION,
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
 *  parser rather than propagate. A recognised envelope with an unsupported
 *  `v` throws `UnsupportedActionProposalVersionError` specifically, so a
 *  caller can tell "this is a future proposal, update your app" apart from
 *  "this isn't a proposal at all". */
export function decodeActionProposal(payload: string): ActionProposal {
  let parsed: unknown
  try {
    parsed = JSON.parse(payload)
  } catch {
    throw new Error('not valid JSON')
  }
  if (typeof parsed !== 'object' || parsed === null) throw new Error('not an object')
  const p = parsed as Record<string, unknown>
  if (p.kind !== 'octobot-action-proposal') throw new Error('not an action proposal payload')
  if (p.v !== SUPPORTED_VERSION) throw new UnsupportedActionProposalVersionError(p.v)
  if (!Array.isArray(p.actions) || p.actions.length === 0) throw new Error('malformed action proposal: actions')
  for (const entry of p.actions as unknown[]) {
    if (typeof entry !== 'object' || entry === null || !('configuration' in entry)) {
      throw new Error('malformed action proposal: entry')
    }
  }
  if (typeof p.createdAt !== 'string') throw new Error('malformed action proposal: createdAt')
  return p as unknown as ActionProposal
}
