import {
  type ActionProposal,
  decodeActionProposal,
  isQrFrame,
  newUserActionId,
  type ProposedActionEntry,
  sleep,
  UnsupportedActionProposalVersionError,
} from "@drakkar.software/octobot-client/protocol"

import type { DebugState, UserAction } from "@/client"
import {
  getUserActionResultErrorDetails,
  getUserActionResultErrorMessage,
  getUserActionUpdatedAt,
} from "@/lib/debug/user-action"

/** A phone that could not append this action to the node directly (a
 *  read-only session) hands it over as a scanned or pasted `ActionProposal`
 *  — see `@drakkar.software/octobot-client`'s protocol/qr-transport docs.
 *  Parsing here mirrors the phone's own decode path exactly, plus one
 *  paste-specific case it never needs: a single decoded QR frame, which
 *  looks nothing like JSON and needs its own message rather than a generic
 *  parse error. */
export type ParsedProposal =
  | { ok: true; proposal: ActionProposal }
  | {
      ok: false
      reason: "empty" | "frame" | "unsupported-version" | "invalid"
      detail?: string
    }

export function parseProposalText(text: string): ParsedProposal {
  const trimmed = text.trim()
  if (!trimmed) return { ok: false, reason: "empty" }
  if (isQrFrame(trimmed)) return { ok: false, reason: "frame" }
  try {
    return { ok: true, proposal: decodeActionProposal(trimmed) }
  } catch (error) {
    if (error instanceof UnsupportedActionProposalVersionError) {
      return { ok: false, reason: "unsupported-version" }
    }
    return {
      ok: false,
      reason: "invalid",
      detail: error instanceof Error ? error.message : String(error),
    }
  }
}

export type ProposalStepState =
  | "waiting"
  | "submitting"
  | "running"
  | "completed"
  | "failed"
  | "skipped"

/** Shared with `waitForConfirmed`'s per-barrier deadline in octobot-sdk's
 *  `executeActionProposal`, but not the same budget: that one computes a
 *  single deadline before the loop and every `previous-confirmed` barrier in
 *  a proposal shares it, so a slow first step starves the rest of a 3-deep
 *  chain (account creation: auth -> exchange_config -> account). This UI
 *  shows a per-step waiting state, so each barrier gets its own full budget
 *  instead. */
const PROPOSAL_STEP_TIMEOUT_MS = 60_000

/** Execution here is node-local (no sync round trip to wait out), so this
 *  ramps faster than octobot-sdk's own `pollDelay` (2s -> 8s, tuned for a
 *  sync pull): 1s -> 4s. `sleep` itself has no reason to diverge, so it's
 *  imported from the same package rather than hand-rolled here. */
function pollDelayMs(attempt: number): number {
  return Math.min(1000 + attempt * 1000, 4000)
}

function toMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

/** A specific step the node executed and rejected. Not retriable by running
 *  the same proposal again unchanged — same distinction octobot-sdk's
 *  `ProposalActionFailedError` draws for the phone's own execution path. */
export class ProposalStepFailedError extends Error {
  constructor(
    public readonly index: number,
    public readonly detail: string,
  ) {
    super(`step ${index + 1} failed${detail ? `: ${detail}` : ""}`)
    this.name = "ProposalStepFailedError"
  }
}

/** Neither step failed outright — the node just never confirmed within the
 *  budget. Worth running again, not evidence the step is broken. */
export class ProposalStepTimeoutError extends Error {
  constructor(public readonly index: number) {
    super(`timed out waiting for step ${index + 1} to complete`)
    this.name = "ProposalStepTimeoutError"
  }
}

function newestRowForId(
  rows: UserAction[],
  id: string,
): UserAction | undefined {
  // The scheduler can report the same id more than once while a workflow
  // moves from non-terminal to terminal — take the newest by the same
  // updated_at precedence the rest of the debug view already uses.
  let newest: UserAction | undefined
  let newestTime = Number.NEGATIVE_INFINITY
  for (const row of rows) {
    if (row.id !== id) continue
    const stamp = getUserActionUpdatedAt(row)
    const time = stamp ? Date.parse(stamp) : Number.NaN
    if (!newest || (Number.isFinite(time) && time >= newestTime)) {
      newest = row
      if (Number.isFinite(time)) newestTime = time
    }
  }
  return newest
}

function stepFailureDetail(row: UserAction): string {
  const details = getUserActionResultErrorDetails(row.result)
  if (details !== "—") return details
  const message = getUserActionResultErrorMessage(row.result)
  return message !== "—" ? message : ""
}

async function waitForStepConfirmed(
  id: string,
  index: number,
  fetchDebugState: () => Promise<DebugState>,
  signal?: AbortSignal,
): Promise<void> {
  const deadline = Date.now() + PROPOSAL_STEP_TIMEOUT_MS
  for (let attempt = 0; ; attempt++) {
    if (signal?.aborted) throw new DOMException("aborted", "AbortError")
    if (Date.now() >= deadline) throw new ProposalStepTimeoutError(index)
    await sleep(pollDelayMs(attempt))
    if (signal?.aborted) throw new DOMException("aborted", "AbortError")

    let state: DebugState
    try {
      state = await fetchDebugState()
    } catch {
      continue // transient — keep polling until the deadline
    }
    const row = newestRowForId(state.debug?.user_actions ?? [], id)
    if (!row) continue // in flight: a non-terminal row echoes the submitted
    // payload, so it has no status of its own — see runActionProposal below.
    if (row.status === "failed")
      throw new ProposalStepFailedError(index, stepFailureDetail(row))
    if (row.status === "completed") return
  }
}

function markSkippedFrom(
  entries: ProposedActionEntry[],
  from: number,
  onStep: (index: number, state: ProposalStepState) => void,
): void {
  for (let i = from; i < entries.length; i++) onStep(i, "skipped")
}

/** Both failure sites in the loop below do the same two things once they
 *  have a `detail` string: mark the failing step, then mark everything
 *  after it skipped. The caller still rethrows its own error afterward, so
 *  a discriminated error class (`ProposalStepFailedError`,
 *  `ProposalStepTimeoutError`) survives out of `runActionProposal` intact. */
function failFrom(
  entries: ProposedActionEntry[],
  onStep: RunActionProposalContext["onStep"],
  index: number,
  detail: string,
): void {
  onStep(index, "failed", detail)
  markSkippedFrom(entries, index + 1, onStep)
}

export type RunActionProposalContext = {
  /** POST one entry's configuration to the node under a fresh id. Throwing
   *  aborts the whole proposal — the caller decides how to render the
   *  error (a 404 here means debug routes are off, see
   *  `_ensure_debug_routes_enabled` on the node). */
  submit: (userAction: {
    id: string
    configuration: ProposedActionEntry["configuration"]
  }) => Promise<void>
  fetchDebugState: () => Promise<DebugState>
  onStep: (index: number, state: ProposalStepState, detail?: string) => void
  signal?: AbortSignal
}

/** Execute every entry of a decoded proposal against this node, in order.
 *  Each entry is submitted only after the previous one has been fully
 *  polled to `completed` — unlike octobot-sdk's `executeActionProposal`
 *  (which only waits before an entry explicitly tagged
 *  `after: 'previous-confirmed'`, since its local outbox has no other way
 *  to observe progress), this UI shows a live per-step status, so every
 *  entry gets the same full wait regardless of that tag. That makes an
 *  explicit `after`-gated wait redundant here — by the time a chained entry
 *  is reached, the entry before it is already known `completed` — so this
 *  does not re-check it; `after` is read only by the dialog, to draw the
 *  connector between two steps that are dependent by design.
 *
 *  A fresh id is minted per entry (never the deterministic `ua-edit-<id>`
 *  style ids this UI's own templates use, which would collide with a prior
 *  run of the same action and make status polling read a stale row). A
 *  failed or timed-out step stops the chain; every entry after it is
 *  reported `skipped`, never submitted. Aborting via `ctx.signal` (the
 *  dialog closing mid-run) stops before the next entry and marks the rest
 *  `skipped` without throwing — there is nothing left to report to. */
export async function runActionProposal(
  proposal: ActionProposal,
  ctx: RunActionProposalContext,
): Promise<void> {
  const entries = proposal.actions
  entries.forEach((_, index) => {
    ctx.onStep(index, "waiting")
  })

  for (let index = 0; index < entries.length; index++) {
    if (ctx.signal?.aborted) {
      markSkippedFrom(entries, index, ctx.onStep)
      return
    }

    const entry = entries[index]
    const id = newUserActionId()
    ctx.onStep(index, "submitting")
    try {
      await ctx.submit({ id, configuration: entry.configuration })
    } catch (error) {
      failFrom(entries, ctx.onStep, index, toMessage(error))
      throw error
    }

    ctx.onStep(index, "running")
    try {
      await waitForStepConfirmed(id, index, ctx.fetchDebugState, ctx.signal)
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        markSkippedFrom(entries, index, ctx.onStep)
        return
      }
      const detail =
        error instanceof ProposalStepFailedError
          ? error.detail
          : toMessage(error)
      failFrom(entries, ctx.onStep, index, detail)
      throw error
    }
    ctx.onStep(index, "completed")
  }
}
