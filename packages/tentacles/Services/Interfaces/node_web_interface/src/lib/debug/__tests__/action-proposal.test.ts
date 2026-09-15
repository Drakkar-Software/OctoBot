import { encodeActionProposal } from "@drakkar.software/octobot-client/protocol"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import type { DebugState, UserAction } from "@/client"
import {
  ProposalStepFailedError,
  ProposalStepTimeoutError,
  parseProposalText,
  runActionProposal,
} from "@/lib/debug/action-proposal"

function makeProposal(
  actions: Array<{ actionType: string; after?: "previous-confirmed" }>,
) {
  const payload = encodeActionProposal(
    actions.map(({ actionType, after }) => ({
      configuration: { action_type: actionType } as never,
      ...(after ? { after } : {}),
    })),
  )
  const parsed = parseProposalText(payload)
  if (!parsed.ok) throw new Error("test fixture failed to parse")
  return parsed.proposal
}

type StepEvent = { index: number; state: string; detail?: string }

/** Each step's state is a sequence (waiting -> submitting -> running ->
 *  completed/failed/skipped) — assertions care about where it ended up. */
function lastStepFor(steps: StepEvent[], index: number): StepEvent | undefined {
  return [...steps].reverse().find((s) => s.index === index)
}

function makeRunHarness() {
  const rowsById = new Map<string, UserAction[]>()
  const submitted: string[] = []
  const steps: StepEvent[] = []

  const submit = vi.fn(
    async ({ id }: { id: string; configuration: unknown }) => {
      submitted.push(id)
    },
  )
  const fetchDebugState = vi.fn(
    async (): Promise<DebugState> => ({
      version: "1",
      debug: {
        automations: [],
        user_actions: [...rowsById.values()].flat(),
      },
    }),
  )
  const onStep = (index: number, state: string, detail?: string) => {
    steps.push({ index, state, detail })
  }

  return {
    submitted,
    steps,
    submit,
    fetchDebugState,
    onStep,
    setRow(id: string, row: Partial<UserAction>) {
      rowsById.set(id, [{ id, ...row } as UserAction])
    },
  }
}

describe("parseProposalText", () => {
  it("reports empty for blank input", () => {
    expect(parseProposalText("   ")).toEqual({ ok: false, reason: "empty" })
  })

  it("recognises a single decoded QR frame and does not treat it as JSON", () => {
    const frame = 'OBQR2|p|deadbeef|00|02|{"v":1'
    expect(parseProposalText(frame)).toEqual({ ok: false, reason: "frame" })
  })

  it("distinguishes an unsupported proposal version from a malformed payload", () => {
    const futureProposal = JSON.stringify({
      v: 2,
      kind: "octobot-action-proposal",
      actions: [{ configuration: {} }],
      createdAt: new Date(0).toISOString(),
    })
    expect(parseProposalText(futureProposal)).toEqual({
      ok: false,
      reason: "unsupported-version",
    })
  })

  it("reports invalid with a detail for anything else unparseable", () => {
    const result = parseProposalText("not json at all")
    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.reason).toBe("invalid")
      expect(result.detail).toBeTruthy()
    }
  })

  it("parses a real encoded proposal", () => {
    const proposal = makeProposal([{ actionType: "automation_stop" }])
    const result = parseProposalText(JSON.stringify(proposal))
    expect(result).toEqual({ ok: true, proposal })
  })
})

describe("runActionProposal", () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it("submits a single entry and resolves once the node confirms it", async () => {
    const h = makeRunHarness()
    const proposal = makeProposal([{ actionType: "automation_stop" }])

    const done = runActionProposal(proposal, h)
    await vi.advanceTimersByTimeAsync(0)
    expect(h.submitted).toHaveLength(1)

    h.setRow(h.submitted[0], { status: "completed" })
    await vi.advanceTimersByTimeAsync(5_000)
    await done

    expect(h.steps.filter((s) => s.state === "completed")).toHaveLength(1)
  })

  it("withholds a previous-confirmed entry until the prior step is confirmed", async () => {
    const h = makeRunHarness()
    const proposal = makeProposal([
      { actionType: "strategy_create" },
      { actionType: "automation_create", after: "previous-confirmed" },
    ])

    const done = runActionProposal(proposal, h)
    await vi.advanceTimersByTimeAsync(0)
    expect(h.submitted).toHaveLength(1)

    // Still not confirmed — the second entry must not be submitted yet.
    await vi.advanceTimersByTimeAsync(5_000)
    expect(h.submitted).toHaveLength(1)

    h.setRow(h.submitted[0], { status: "completed" })
    await vi.advanceTimersByTimeAsync(5_000)
    expect(h.submitted).toHaveLength(2)

    h.setRow(h.submitted[1], { status: "completed" })
    await vi.advanceTimersByTimeAsync(5_000)
    await done

    expect(h.steps.filter((s) => s.state === "completed")).toHaveLength(2)
  })

  it("aborts the chain on a failed step and marks the rest skipped", async () => {
    const h = makeRunHarness()
    const proposal = makeProposal([
      { actionType: "strategy_create" },
      { actionType: "automation_create", after: "previous-confirmed" },
    ])

    const done = runActionProposal(proposal, h)
    const assertion = expect(done).rejects.toBeInstanceOf(
      ProposalStepFailedError,
    )
    await vi.advanceTimersByTimeAsync(0)
    h.setRow(h.submitted[0], {
      status: "failed",
      result: {
        actual_instance: { error_details: "strategy not found" },
      } as never,
    })
    await vi.advanceTimersByTimeAsync(5_000)
    await assertion

    expect(h.submitted).toHaveLength(1) // the chained entry never went out
    expect(lastStepFor(h.steps, 0)?.state).toBe("failed")
    expect(lastStepFor(h.steps, 0)?.detail).toContain("strategy not found")
    expect(lastStepFor(h.steps, 1)?.state).toBe("skipped")
  })

  it("takes the newest of duplicate rows for the same id", async () => {
    const h = makeRunHarness()
    const proposal = makeProposal([{ actionType: "automation_stop" }])

    const done = runActionProposal(proposal, h)
    await vi.advanceTimersByTimeAsync(0)
    const id = h.submitted[0]

    // An older, still-pending row and a newer, completed one for the same id.
    h.fetchDebugState.mockImplementation(async () => ({
      version: "1",
      debug: {
        automations: [],
        user_actions: [
          { id, created_at: "2026-01-01T00:00:00.000Z" } as UserAction,
          {
            id,
            status: "completed",
            updated_at: "2026-01-01T00:05:00.000Z",
          } as UserAction,
        ],
      },
    }))
    await vi.advanceTimersByTimeAsync(5_000)
    await done

    expect(h.steps.filter((s) => s.state === "completed")).toHaveLength(1)
  })

  it("times out a step that never confirms", async () => {
    const h = makeRunHarness()
    const proposal = makeProposal([{ actionType: "automation_stop" }])

    const done = runActionProposal(proposal, h)
    const assertion = expect(done).rejects.toBeInstanceOf(
      ProposalStepTimeoutError,
    )
    await vi.advanceTimersByTimeAsync(65_000)
    await assertion

    expect(lastStepFor(h.steps, 0)?.state).toBe("failed")
  })

  it("marks the rest skipped when submitting a step itself throws", async () => {
    const h = makeRunHarness()
    h.submit.mockRejectedValueOnce(
      new Error(
        "Debug actions are turned off while node-side encryption is on.",
      ),
    )
    const proposal = makeProposal([
      { actionType: "strategy_create" },
      { actionType: "automation_create", after: "previous-confirmed" },
    ])

    const done = runActionProposal(proposal, h)
    await expect(done).rejects.toThrow(
      "Debug actions are turned off while node-side encryption is on.",
    )
    expect(lastStepFor(h.steps, 0)?.state).toBe("failed")
    expect(lastStepFor(h.steps, 1)?.state).toBe("skipped")
  })

  it("stops without rejecting when the caller aborts mid-run", async () => {
    const h = makeRunHarness()
    const proposal = makeProposal([
      { actionType: "strategy_create" },
      { actionType: "automation_create", after: "previous-confirmed" },
    ])
    const controller = new AbortController()

    const done = runActionProposal(proposal, {
      ...h,
      signal: controller.signal,
    })
    await vi.advanceTimersByTimeAsync(0)
    expect(h.submitted).toHaveLength(1)

    controller.abort()
    await vi.advanceTimersByTimeAsync(5_000)
    await done // resolves — an intentional stop is not a failure

    expect(h.submitted).toHaveLength(1) // the second entry never went out
    expect(lastStepFor(h.steps, 0)?.state).toBe("skipped")
    expect(lastStepFor(h.steps, 1)?.state).toBe("skipped")
  })
})
