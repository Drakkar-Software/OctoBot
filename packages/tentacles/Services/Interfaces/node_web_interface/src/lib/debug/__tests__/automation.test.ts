import { describe, expect, it } from "vitest"

import type { Action, AutomationState } from "@/client"
import {
  formatActionProgress,
  getActionExecutionStats,
  getAutomationActions,
  getAutomationErrorTooltipLines,
  getAutomationUpdatedAt,
  getLatestExecutedAction,
  getNextPendingAction,
  getRunningAction,
  isActionExecuted,
  isRunningAutomation,
  signalTypeRequiresPayload,
  validateAutomationCanReceiveSignal,
} from "@/lib/debug/automation"

function makeAutomation(
  overrides: Partial<AutomationState> = {},
): AutomationState {
  return {
    id: "auto-1",
    status: "running",
    metadata: { name: "Test", description: "" },
    ...overrides,
  }
}

describe("signalTypeRequiresPayload", () => {
  it("requires payload for actions and trading_signal", () => {
    expect(signalTypeRequiresPayload("actions")).toBe(true)
    expect(signalTypeRequiresPayload("trading_signal")).toBe(true)
    expect(signalTypeRequiresPayload("forced_trigger")).toBe(false)
  })
})

describe("isRunningAutomation", () => {
  it("returns true only for running status", () => {
    expect(isRunningAutomation(makeAutomation({ status: "running" }))).toBe(
      true,
    )
    expect(isRunningAutomation(makeAutomation({ status: "completed" }))).toBe(
      false,
    )
  })
})

describe("getAutomationActions", () => {
  it("returns an empty array when actions are missing", () => {
    expect(getAutomationActions(makeAutomation())).toEqual([])
  })
})

describe("isActionExecuted", () => {
  it("treats completed_at or completed status as executed", () => {
    expect(
      isActionExecuted({
        id: "a1",
        action_type: "noop",
        status: "pending",
        completed_at: "2024-01-01T00:00:00.000Z",
      }),
    ).toBe(true)
    expect(
      isActionExecuted({ id: "a2", action_type: "noop", status: "completed" }),
    ).toBe(true)
  })
})

describe("getActionExecutionStats", () => {
  it("counts executed and total actions", () => {
    const stats = getActionExecutionStats(
      makeAutomation({
        actions: [
          { id: "a1", action_type: "noop", status: "completed" },
          { id: "a2", action_type: "noop", status: "pending" },
        ],
      }),
    )
    expect(stats).toEqual({ executed: 1, total: 2 })
  })
})

describe("getLatestExecutedAction", () => {
  it("returns the action with the latest completed_at", () => {
    const actions: Action[] = [
      {
        id: "a1",
        action_type: "noop",
        status: "completed",
        completed_at: "2024-01-01T00:00:00.000Z",
      },
      {
        id: "a2",
        action_type: "noop",
        status: "completed",
        completed_at: "2024-06-01T00:00:00.000Z",
      },
    ]
    expect(getLatestExecutedAction(actions)?.id).toBe("a2")
  })
})

describe("getNextPendingAction", () => {
  it("returns the first action without completed_at", () => {
    const actions: Action[] = [
      {
        id: "a1",
        action_type: "noop",
        status: "completed",
        completed_at: "2024-01-01T00:00:00.000Z",
      },
      { id: "a2", action_type: "noop", status: "pending" },
    ]
    expect(getNextPendingAction(actions)?.id).toBe("a2")
  })
})

describe("getRunningAction", () => {
  it("returns the first running action", () => {
    const actions: Action[] = [
      { id: "a1", action_type: "noop", status: "pending" },
      { id: "a2", action_type: "noop", status: "running" },
    ]
    expect(getRunningAction(actions)?.id).toBe("a2")
  })
})

describe("getAutomationUpdatedAt", () => {
  it("prefers metadata.updated_at", () => {
    expect(
      getAutomationUpdatedAt(
        makeAutomation({
          metadata: {
            name: "Bot",
            description: "",
            updated_at: "2024-05-01T00:00:00.000Z",
          },
          actions: [
            {
              id: "a1",
              action_type: "noop",
              status: "completed",
              completed_at: "2024-06-01T00:00:00.000Z",
            },
          ],
        }),
      ),
    ).toBe("2024-05-01T00:00:00.000Z")
  })
})

describe("formatActionProgress", () => {
  it("formats executed/total counts", () => {
    expect(
      formatActionProgress(
        makeAutomation({
          actions: [
            { id: "a1", action_type: "noop", status: "completed" },
            { id: "a2", action_type: "noop", status: "pending" },
          ],
        }),
      ),
    ).toBe("1/2")
  })
})

describe("getAutomationErrorTooltipLines", () => {
  it("includes error and error_message lines", () => {
    expect(
      getAutomationErrorTooltipLines(
        makeAutomation({
          error: "timeout",
          error_message: "deadline exceeded",
        }),
      ),
    ).toEqual(["error: timeout", "error_message: deadline exceeded"])
  })
})

describe("validateAutomationCanReceiveSignal", () => {
  it("rejects non-running automations", () => {
    expect(
      validateAutomationCanReceiveSignal(
        makeAutomation({ status: "completed" }),
      ),
    ).toBe("Only running automations can receive signals.")
  })

  it("returns null for running automations", () => {
    expect(validateAutomationCanReceiveSignal(makeAutomation())).toBeNull()
  })
})
