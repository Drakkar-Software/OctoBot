import { describe, expect, it } from "vitest"

import { buildSignalUserActionConfiguration } from "@/lib/debug/execute-user-action"

describe("buildSignalUserActionConfiguration", () => {
  it("builds a forced trigger configuration without payload", () => {
    const result = buildSignalUserActionConfiguration(
      "auto-1",
      "forced_trigger",
    )
    expect("configuration" in result).toBe(true)
    if ("configuration" in result) {
      expect(result.configuration).toMatchObject({
        action_type: "automation_signal",
        automation_id: "auto-1",
        signal_type: "forced_trigger",
      })
    }
  })

  it("parses JSON payload for actions signal type", () => {
    const result = buildSignalUserActionConfiguration(
      "auto-1",
      "actions",
      '[{"id":"action_1","dsl_script":"noop()"}]',
    )
    expect("configuration" in result).toBe(true)
    if ("configuration" in result) {
      expect(
        (result.configuration as Record<string, unknown>).signal_payload,
      ).toEqual([{ id: "action_1", dsl_script: "noop()" }])
    }
  })

  it("returns an error for invalid JSON payload", () => {
    const result = buildSignalUserActionConfiguration(
      "auto-1",
      "trading_signal",
      "{",
    )
    expect("error" in result).toBe(true)
  })

  it("requires payload text for payload signal types", () => {
    const result = buildSignalUserActionConfiguration("auto-1", "actions", "  ")
    expect(result).toEqual({
      error: "Signal payload is required for this signal type.",
    })
  })
})
