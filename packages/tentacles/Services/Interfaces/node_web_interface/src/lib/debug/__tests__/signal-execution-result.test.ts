import { describe, expect, it } from "vitest"

import type { UserAction } from "@/client"
import {
  formatSignalExecutionResultTooltipLines,
  formatSignalExecutionResultsSummary,
  getAutomationActionResult,
  getSignalExecutionResults,
  isSuccessfulSignalPriorityActionResult,
} from "@/lib/debug/signal-execution-result"

describe("isSuccessfulSignalPriorityActionResult", () => {
  it("treats null and no_error as success", () => {
    expect(
      isSuccessfulSignalPriorityActionResult({
        priority_action_id: "action_1",
        error_status: null,
      }),
    ).toBe(true)
    expect(
      isSuccessfulSignalPriorityActionResult({
        priority_action_id: "action_1",
        error_status: "no_error",
      }),
    ).toBe(true)
  })

  it("treats other error_status values as failure", () => {
    expect(
      isSuccessfulSignalPriorityActionResult({
        priority_action_id: "action_1",
        error_status: "not_enough_funds",
      }),
    ).toBe(false)
  })
})

describe("getAutomationActionResult", () => {
  it("unwraps actual_instance oneOf payloads", () => {
    const result = {
      actual_instance: {
        updated_at: "2026-01-01T00:00:00Z",
        result_type: "automation",
        signal_execution_results: [
          { priority_action_id: "action_1", error_status: "no_error" },
        ],
      },
    } as UserAction["result"]

    expect(getAutomationActionResult(result)?.signal_execution_results).toHaveLength(
      1,
    )
  })
})

describe("getSignalExecutionResults", () => {
  it("returns an empty array when signal results are missing", () => {
    expect(getSignalExecutionResults(undefined)).toEqual([])
    expect(getSignalExecutionResults(null)).toEqual([])
  })
})

describe("formatSignalExecutionResultsSummary", () => {
  it("formats all-success, all-failed, and mixed summaries", () => {
    expect(
      formatSignalExecutionResultsSummary([
        { priority_action_id: "a1", error_status: "no_error" },
        { priority_action_id: "a2", error_status: null },
      ]),
    ).toBe("2 OK")
    expect(
      formatSignalExecutionResultsSummary([
        {
          priority_action_id: "a1",
          error_status: "not_enough_funds",
        },
      ]),
    ).toBe("1 failed")
    expect(
      formatSignalExecutionResultsSummary([
        { priority_action_id: "a1", error_status: "no_error" },
        {
          priority_action_id: "a2",
          error_status: "not_enough_funds",
        },
      ]),
    ).toBe("1 OK · 1 failed")
    expect(formatSignalExecutionResultsSummary([])).toBe("—")
  })
})

describe("formatSignalExecutionResultTooltipLines", () => {
  it("includes status and message for failed actions", () => {
    const lines = formatSignalExecutionResultTooltipLines([
      {
        priority_action_id: "action_not_enough_funds",
        error_status: "not_enough_funds",
        error_message: "Not enough funds for 0.0001 amount",
      },
    ])
    expect(lines).toHaveLength(1)
    expect(lines[0]).toContain("action_not_enough_funds")
    expect(lines[0]).toContain("not_enough_funds")
    expect(lines[0]).toContain("Not enough funds for 0.0001 amount")
  })

  it("marks successful actions as OK", () => {
    const lines = formatSignalExecutionResultTooltipLines([
      { priority_action_id: "action_ok", error_status: "no_error" },
    ])
    expect(lines[0]).toContain("action_ok")
    expect(lines[0]).toContain("OK")
  })
})
