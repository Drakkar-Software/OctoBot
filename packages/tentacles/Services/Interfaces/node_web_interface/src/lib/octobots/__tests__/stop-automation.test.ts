import { describe, expect, it } from "vitest"

import { ApiError } from "@/client"
import {
  buildStopAutomationUserAction,
  canStopOctoBot,
  formatStopAutomationError,
  getStopAutomationConfigurationActionType,
  getOctoBotDisplayName,
  getStopAutomationTargetId,
} from "../stop-automation"

describe("canStopOctoBot", () => {
  it("returns true for active execution statuses", () => {
    for (const status of ["pending", "running", "scheduled", "periodic"] as const) {
      expect(
        canStopOctoBot({
          id: "auto-1",
          executions: [{ id: "exec-1", status, scheduled_at: "2026-01-01T00:00:00Z" }],
        }),
      ).toBe(true)
    }
  })

  it("returns false for completed and failed executions", () => {
    expect(
      canStopOctoBot({
        id: "auto-1",
        executions: [
          {
            id: "exec-1",
            status: "completed",
            scheduled_at: "2026-01-01T00:00:00Z",
            completed_at: "2026-01-01T01:00:00Z",
          },
        ],
      }),
    ).toBe(false)
    expect(
      canStopOctoBot({
        id: "auto-1",
        executions: [
          {
            id: "exec-1",
            status: "failed",
            scheduled_at: "2026-01-01T00:00:00Z",
            completed_at: "2026-01-01T01:00:00Z",
          },
        ],
      }),
    ).toBe(false)
  })
})


describe("getOctoBotDisplayName", () => {
  it("prefers task name, then active execution name, then id fallback", () => {
    expect(
      getOctoBotDisplayName({
        id: "auto-123456",
        name: "My bot",
        executions: [{ id: "exec-1", status: "running", name: "Exec name" }],
      }),
    ).toBe("My bot")
    expect(
      getOctoBotDisplayName({
        id: "auto-123456",
        executions: [{ id: "exec-1", status: "running", name: "Exec name" }],
      }),
    ).toBe("Exec name")
    expect(
      getOctoBotDisplayName({
        id: "auto-123456",
        executions: [{ id: "exec-1", status: "running" }],
      }),
    ).toBe("OctoBot auto-1")
  })
})

describe("buildStopAutomationUserAction", () => {
  it("builds an automation_stop user action for the automation id", () => {
    const userAction = buildStopAutomationUserAction("auto-1")
    expect(userAction.id).toMatch(/^ua-stop-auto-1-[0-9a-f-]{36}$/)
    expect(getStopAutomationConfigurationActionType(userAction)).toBe(
      "automation_stop",
    )
    expect(getStopAutomationTargetId(userAction)).toBe("auto-1")
  })
})

describe("formatStopAutomationError", () => {
  it("uses string detail from ApiError", () => {
    const error = new ApiError(
      { method: "POST", url: "/api/v1/debug/" },
      {
        url: "/api/v1/debug/",
        ok: false,
        status: 400,
        statusText: "Bad Request",
        body: { detail: "automation not found" },
      },
      "Bad Request",
    )
    expect(formatStopAutomationError(error)).toBe("automation not found")
  })

  it("uses validation array detail from ApiError", () => {
    const error = new ApiError(
      { method: "POST", url: "/api/v1/debug/" },
      {
        url: "/api/v1/debug/",
        ok: false,
        status: 422,
        statusText: "Unprocessable Entity",
        body: { detail: [{ msg: "Invalid user action" }] },
      },
      "Unprocessable Entity",
    )
    expect(formatStopAutomationError(error)).toBe("Invalid user action")
  })

  it("falls back to a generic message", () => {
    expect(formatStopAutomationError({})).toBe(
      "Couldn't stop this OctoBot. Try again.",
    )
  })
})
