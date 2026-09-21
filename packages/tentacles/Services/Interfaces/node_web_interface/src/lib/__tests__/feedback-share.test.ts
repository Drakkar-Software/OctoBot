import { unzipSync } from "fflate"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import type { FeedbackPreviewResponse, FeedbackUploadEnvelope } from "@/client"
import {
  buildContactNoteSuffix,
  buildContextNotePrefix,
  buildFeedbackFilename,
  buildFeedbackMailtoUrl,
  buildFeedbackNote,
  buildNodeJournalZipBytes,
  buildRecoveryFeedbackFallbackEnvelope,
  computeShareFeedbackSendDisabled,
  downloadFeedbackEnvelope,
  downloadPreviewEnvelope,
  FEEDBACK_JOURNAL_JSON_FILENAME,
  FEEDBACK_JOURNAL_ZIP_FILENAME,
  formatJourneySummaryForDisplay,
  getPreviewEventCount,
  getPreviewAutomationCount,
  getShareFeedbackUiErrorName,
  resolveShareFeedbackUiErrorRoute,
} from "@/lib/feedback-share"

describe("computeShareFeedbackSendDisabled", () => {
  it("allows send with empty journal when note is present", () => {
    expect(
      computeShareFeedbackSendDisabled({
        submitPending: false,
        useDegradedRecoveryFeedback: false,
        hasUiErrorContext: false,
        showSignInPrompt: false,
        previewLoading: false,
        previewError: false,
        hasPreview: true,
        eventCount: 0,
        note: "Something broke",
      }),
    ).toBe(false)
  })

  it("disables send with empty journal and empty note", () => {
    expect(
      computeShareFeedbackSendDisabled({
        submitPending: false,
        useDegradedRecoveryFeedback: false,
        hasUiErrorContext: false,
        showSignInPrompt: false,
        previewLoading: false,
        previewError: false,
        hasPreview: true,
        eventCount: 0,
        note: "",
      }),
    ).toBe(true)
  })

  it("allows send with empty journal and empty note when ui error context is set", () => {
    expect(
      computeShareFeedbackSendDisabled({
        submitPending: false,
        useDegradedRecoveryFeedback: false,
        hasUiErrorContext: true,
        showSignInPrompt: false,
        previewLoading: false,
        previewError: false,
        hasPreview: true,
        eventCount: 0,
        note: "",
      }),
    ).toBe(false)
  })
})

describe("getShareFeedbackUiErrorName", () => {
  it("returns failure kind for recovery contexts", () => {
    expect(
      getShareFeedbackUiErrorName({
        source: "recovery",
        failureKind: "boot_failed",
      }),
    ).toBe("boot_failed")
    expect(
      getShareFeedbackUiErrorName({
        source: "recovery",
        failureKind: "insecure_context",
      }),
    ).toBe("insecure_context")
  })

  it("returns route_error for route error context", () => {
    expect(
      getShareFeedbackUiErrorName({
        source: "route_error",
        routePath: "/app",
      }),
    ).toBe("route_error")
  })

  it("returns null for navbar and settings", () => {
    expect(getShareFeedbackUiErrorName({ source: "navbar" })).toBeNull()
    expect(getShareFeedbackUiErrorName({ source: "settings" })).toBeNull()
  })
})

describe("resolveShareFeedbackUiErrorRoute", () => {
  it("uses pathname from location for navbar and settings", () => {
    expect(
      resolveShareFeedbackUiErrorRoute(
        { source: "navbar" },
        { pathname: "/app/settings" },
      ),
    ).toBe("/app/settings")
  })

  it("uses pathname for recovery context", () => {
    expect(
      resolveShareFeedbackUiErrorRoute(
        { source: "recovery", failureKind: "boot_failed" },
        { pathname: "/app/setup" },
      ),
    ).toBe("/app/setup")
  })

  it("prefers explicit routePath for route_error", () => {
    expect(
      resolveShareFeedbackUiErrorRoute(
        { source: "route_error", routePath: "/app/x" },
        { pathname: "/other" },
      ),
    ).toBe("/app/x")
  })

  it("falls back to pathname when route_error has no routePath", () => {
    expect(
      resolveShareFeedbackUiErrorRoute(
        { source: "route_error" },
        { pathname: "/app/settings" },
      ),
    ).toBe("/app/settings")
  })

  it("returns null when location is missing", () => {
    expect(resolveShareFeedbackUiErrorRoute({ source: "navbar" })).toBeNull()
  })
})

describe("buildRecoveryFeedbackFallbackEnvelope", () => {
  it("sets required fields for client download", () => {
    const envelope = buildRecoveryFeedbackFallbackEnvelope({
      note: "composed note",
      uiErrorName: "auth_broken",
      uiErrorRoute: null,
    })
    expect(envelope.install_id).toBe("recovery-client-fallback")
    expect(envelope.onboarding_complete).toBe(false)
    expect(envelope.journey_summary).toEqual({
      source: "recovery_client_fallback",
    })
    expect(envelope.event_count).toBe(0)
    expect(envelope.note).toBe("composed note")
    expect(envelope.ui_error_name).toBe("auth_broken")
  })
})

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

  it("formats insecure_context recovery context", () => {
    expect(
      buildContextNotePrefix({
        source: "recovery",
        failureKind: "insecure_context",
      }),
    ).toBe("[ui_context] source=recovery failure_kind=insecure_context")
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

  it("omits ui_context prefix for recovery feedback", () => {
    expect(
      buildFeedbackNote({
        note: "Extra detail",
        context: { source: "recovery", failureKind: "boot_failed" },
      }),
    ).toBe("Extra detail")
  })

  it("omits ui_context prefix for route errors", () => {
    expect(
      buildFeedbackNote({
        context: { source: "route_error", routePath: "/x" },
      }),
    ).toBe("")
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
  it("uses the journal json member name", () => {
    const envelope = {
      install_id: "abcdefgh1234",
    } as FeedbackUploadEnvelope

    expect(buildFeedbackFilename(envelope)).toBe(FEEDBACK_JOURNAL_JSON_FILENAME)
  })
})

describe("buildNodeJournalZipBytes", () => {
  it("builds node_journal.zip bytes with a valid node_journal.json member", () => {
    expect(FEEDBACK_JOURNAL_ZIP_FILENAME).toBe("node_journal.zip")
    const zipBytes = buildNodeJournalZipBytes({
      install_id: "install-1",
      event_count: 0,
    } as FeedbackUploadEnvelope)
    expect(zipBytes[0]).toBe(0x50)
    expect(zipBytes[1]).toBe(0x4b)

    const unzipped = unzipSync(zipBytes)
    expect(Object.keys(unzipped)).toEqual([FEEDBACK_JOURNAL_JSON_FILENAME])
    const jsonText = new TextDecoder().decode(
      unzipped[FEEDBACK_JOURNAL_JSON_FILENAME],
    )
    const parsed = JSON.parse(jsonText) as { install_id: string }
    expect(parsed.install_id).toBe("install-1")
  })

  it("compresses repetitive journal content smaller than raw JSON", () => {
    const envelope = {
      install_id: "install-1",
      app_version: "1.0.0",
      onboarding_started_at: null,
      onboarding_complete: false,
      journey_summary: {},
      uploaded: false,
      ready: true,
      event_count: 50,
      events: Array.from({ length: 50 }, (_, index) => ({
        event: "wallet_setup_succeeded",
        attributes: { note: "x".repeat(200) },
        timestamp: index,
      })),
    } as FeedbackUploadEnvelope
    const rawJson = JSON.stringify(envelope, null, 2)
    const zipBytes = buildNodeJournalZipBytes(envelope)
    expect(zipBytes.length).toBeLessThan(rawJson.length)
  })
})

describe("buildFeedbackMailtoUrl", () => {
  it("includes user note and attach instruction without install id", () => {
    const mailto = buildFeedbackMailtoUrl({
      note: "Something broke",
      contactMethod: "email",
      contactValue: "user@example.com",
    })
    expect(mailto).toContain("mailto:contact@octobot.cloud")
    expect(mailto).toContain("Something+broke")
    expect(mailto).toContain("Email%3A+user%40example.com")
    expect(mailto).toContain("node_journal.zip")
    expect(mailto).not.toContain("install_id")
    expect(mailto).not.toContain("app_version")
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
      body: {
        appendChild: vi.fn(),
        removeChild: vi.fn(),
      },
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
