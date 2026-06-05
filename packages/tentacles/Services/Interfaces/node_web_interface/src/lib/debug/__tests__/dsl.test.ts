import { describe, expect, it } from "vitest"

import type { Action, AutomationState } from "@/client"
import {
  buildCompoundDslSummary,
  extractDslKeywordFromFragment,
  extractFirstDslArgument,
  formatDslSummary,
  getActionDslKeyword,
  getAutomationDslHint,
  isCompoundDslKeyword,
} from "@/lib/debug/dsl"

describe("extractFirstDslArgument", () => {
  it("returns the first top-level argument", () => {
    expect(extractFirstDslArgument("if_error(noop(), fallback())")).toBe(
      "noop()",
    )
  })

  it("returns null when there is no opening parenthesis", () => {
    expect(extractFirstDslArgument("noop")).toBeNull()
  })
})

describe("extractDslKeywordFromFragment", () => {
  it("reads the leading identifier", () => {
    expect(extractDslKeywordFromFragment("  noop()")).toBe("noop")
  })
})

describe("isCompoundDslKeyword", () => {
  it("recognizes compound DSL keywords", () => {
    expect(isCompoundDslKeyword("if_error")).toBe(true)
    expect(isCompoundDslKeyword("noop")).toBe(false)
  })
})

describe("buildCompoundDslSummary", () => {
  it("builds nested summaries for compound keywords", () => {
    expect(
      buildCompoundDslSummary("if_error(loop_until(noop(), 3), fallback())", "if_error"),
    ).toBe("if_error.loop_until.noop")
  })
})

describe("formatDslSummary", () => {
  it("returns em dash for empty input", () => {
    expect(formatDslSummary(null)).toBe("—")
  })

  it("returns the first keyword for simple DSL", () => {
    expect(formatDslSummary("noop()")).toBe("noop")
  })
})

describe("getActionDslKeyword", () => {
  it("prefers DSL summary over action_type", () => {
    const action: Action = {
      id: "a1",
      action_type: "legacy",
      status: "completed",
      dsl: "if_error(noop(), fallback())",
    }
    expect(getActionDslKeyword(action)).toBe("if_error.noop")
  })
})

describe("getAutomationDslHint", () => {
  it("uses the next pending action for running automations", () => {
    const automation: AutomationState = {
      id: "auto-1",
      status: "running",
      metadata: { name: "Bot", description: "" },
      actions: [
        { id: "a1", action_type: "noop", status: "running", dsl: "noop()" },
      ],
    }
    expect(getAutomationDslHint(automation)).toBe("noop")
  })
})
