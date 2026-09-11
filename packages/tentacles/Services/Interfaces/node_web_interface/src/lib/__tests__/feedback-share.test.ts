import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import type { FeedbackPreviewResponse, FeedbackUploadEnvelope } from "@/client"
import {
  buildContactNoteSuffix,
  buildContextNotePrefix,
  buildFeedbackFilename,
  buildFeedbackNote,
  downloadFeedbackEnvelope,
  downloadPreviewEnvelope,
  formatJourneySummaryForDisplay,
  getPreviewEventCount,
  getPreviewAutomationCount,
} from "@/lib/feedback-share"

describe("buildContextNotePrefix", () => {
  it("formats navbar context", () => {
    expect(buildContextNotePrefix({ source: "navbar" })).toBe(
      "[ui_context] source=navbar",
    )
  })

  it("formats settings context", () => {
    expect(buildContextNotePrefix({ source: "settings" })).toBe(
      "[ui_context] source=settings",
    )
  })

  it("formats recovery context", () => {
    expect(
      buildContextNotePrefix({
        source: "recovery",
        failureKind: "boot_failed",
      }),
    ).toBe("[ui_context] source=recovery failure_kind=boot_failed")
  })

  it("formats route error context with route path", () => {
    expect(
      buildContextNotePrefix({
        source: "route_error",
        routePath: "/app/settings",
      }),
    ).toBe("[ui_context] source=route_error route=/app/settings")
  })
})

describe("buildContactNoteSuffix", () => {
  it("returns null when contact fields are empty", () => {
    expect(buildContactNoteSuffix({})).toBeNull()
  })

  it("formats contact method and value", () => {
    expect(
      buildContactNoteSuffix({
        contactMethod: "email",
        contactValue: "user@example.com",
      }),
    ).toBe("[contact] method=email value=user@example.com")
  })

  it("allows method without value", () => {
    expect(
      buildContactNoteSuffix({
        contactMethod: "telegram",
      }),
    ).toBe("[contact] method=telegram value=unspecified")
  })
})

describe("buildFeedbackNote", () => {
  it("merges context, user note, and contact block", () => {
    expect(
      buildFeedbackNote({
        note: "Button stopped responding",
        context: { source: "settings" },
        contactMethod: "discord",
        contactValue: "octotrader",
      }),
    ).toBe(
      "[ui_context] source=settings\n\nButton stopped responding\n\n[contact] method=discord value=octotrader",
    )
  })
})

describe("formatJourneySummaryForDisplay", () => {
  it("omits first failure when missing", () => {
    const lines = formatJourneySummaryForDisplay({
      onboarding_complete: false,
      furthest_step_reached: null,
      ui_blocking_issues_count: 0,
      first_failure: null,
    })
    expect(lines).toEqual([
      "Onboarding complete: no",
      "UI blocking issues: 0",
    ])
  })

  it("formats first failure with truncated message", () => {
    const longMessage = "x".repeat(150)
    const lines = formatJourneySummaryForDisplay({
      onboarding_complete: true,
      furthest_step_reached: "wallet_setup_succeeded",
      ui_blocking_issues_count: 1,
      first_failure: {
        event: "account_validation_failed",
        timestamp: 1_710_000_000,
        error_category: "validation",
        error_message: longMessage,
      },
    })

    expect(lines[0]).toBe("Onboarding complete: yes")
    expect(lines[1]).toBe("Furthest step: wallet_setup_succeeded")
    expect(lines[2]).toBe("UI blocking issues: 1")
    expect(lines[3]).toMatch(/^First failure /)
    expect(lines[3]).toContain("account_validation_failed")
    expect(lines[3]).toContain("validation")
    expect(lines[3]).not.toContain(longMessage)
    expect(lines[3]?.length).toBeLessThan(220)
  })
})

describe("getPreviewEventCount", () => {
  it("reads upload_envelope.event_count", () => {
    const preview = {
      journey_summary: {},
      upload_envelope: {
        event_count: 3,
      },
    } as FeedbackPreviewResponse

    expect(getPreviewEventCount(preview)).toBe(3)
  })
})

describe("getPreviewAutomationCount", () => {
  it("reads automation_count from the latest reconcile_completed event", () => {
    const preview = {
      journey_summary: {},
      upload_envelope: {
        events: [
          {
            event: "wallet_setup_succeeded",
            attributes: {},
          },
          {
            event: "reconcile_completed",
            attributes: { automation_count: 2, running_automation_count: 1 },
          },
          {
            event: "reconcile_completed",
            attributes: { automation_count: 5, running_automation_count: 4 },
          },
        ],
      },
    } as unknown as FeedbackPreviewResponse

    expect(getPreviewAutomationCount(preview)).toBe(5)
  })

  it("returns null when reconcile_completed is missing", () => {
    const preview = {
      journey_summary: {},
      upload_envelope: {
        events: [{ event: "wallet_setup_succeeded", attributes: {} }],
      },
    } as unknown as FeedbackPreviewResponse

    expect(getPreviewAutomationCount(preview)).toBeNull()
  })
})

describe("buildFeedbackFilename", () => {
  it("produces a stable feedback json name", () => {
    const envelope = {
      install_id: "abcdefgh1234",
    } as FeedbackUploadEnvelope

    expect(buildFeedbackFilename(envelope)).toMatch(
      /^feedback-abcdefgh-.+\.json$/,
    )
  })
})

describe("downloadFeedbackEnvelope", () => {
  const createObjectUrlMock = vi.fn(() => "blob:feedback")
  const revokeObjectUrlMock = vi.fn()
  const clickMock = vi.fn()

  beforeEach(() => {
    createObjectUrlMock.mockClear()
    revokeObjectUrlMock.mockClear()
    clickMock.mockClear()
    vi.stubGlobal("URL", {
      createObjectURL: createObjectUrlMock,
      revokeObjectURL: revokeObjectUrlMock,
    })
    vi.stubGlobal("document", {
      createElement: () =>
        ({
          click: clickMock,
          download: "",
          href: "",
        }) as unknown as HTMLAnchorElement,
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("downloads serialized envelope json", () => {
    const envelope = {
      install_id: "abcdefgh",
      event_count: 1,
      uploaded: false,
    } as FeedbackUploadEnvelope

    downloadFeedbackEnvelope(envelope)

    expect(createObjectUrlMock).toHaveBeenCalledTimes(1)
    expect(clickMock).toHaveBeenCalledTimes(1)
    expect(revokeObjectUrlMock).toHaveBeenCalledWith("blob:feedback")
  })

  it("downloads preview upload envelope", () => {
    const preview = {
      journey_summary: {},
      upload_envelope: {
        install_id: "abcdefgh",
        event_count: 2,
      },
    } as FeedbackPreviewResponse

    downloadPreviewEnvelope(preview)

    expect(createObjectUrlMock).toHaveBeenCalledTimes(1)
    expect(clickMock).toHaveBeenCalledTimes(1)
  })
})
