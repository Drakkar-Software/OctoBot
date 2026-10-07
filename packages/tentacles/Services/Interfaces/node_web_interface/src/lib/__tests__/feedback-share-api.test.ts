import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import type { FeedbackUploadEnvelope } from "@/client"
import {
  FEEDBACK_JOURNAL_JSON_FILENAME,
  FEEDBACK_JOURNAL_ZIP_FILENAME,
  submitFeedbackDownload,
} from "@/lib/feedback-share"

const assignMock = vi.fn()
const fetchMock = vi.fn()

const MINIMAL_ZIP_BYTES = new Uint8Array([0x50, 0x4b, 0x03, 0x04])

function stubWindowPathname(pathname: string) {
  vi.stubGlobal("window", {
    location: {
      pathname,
      assign: assignMock,
    },
  })
}

describe("submitFeedbackDownload", () => {
  const createObjectUrlMock = vi.fn(() => "blob:feedback")
  const revokeObjectUrlMock = vi.fn()
  const clickMock = vi.fn()
  let createdLink: HTMLAnchorElement

  beforeEach(() => {
    fetchMock.mockReset()
    createObjectUrlMock.mockClear()
    revokeObjectUrlMock.mockClear()
    clickMock.mockClear()
    assignMock.mockClear()
    vi.stubGlobal("fetch", fetchMock)
    vi.stubGlobal("URL", {
      createObjectURL: createObjectUrlMock,
      revokeObjectURL: revokeObjectUrlMock,
    })
    vi.stubGlobal("document", {
      body: {
        appendChild: vi.fn(),
        removeChild: vi.fn(),
      },
      createElement: () => {
        createdLink = {
          click: clickMock,
          download: "",
          href: "",
        } as unknown as HTMLAnchorElement
        return createdLink
      },
    })
    vi.stubGlobal("window", {
      location: {
        pathname: "/app",
        assign: assignMock,
      },
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("downloads zip when export succeeds", async () => {
    stubWindowPathname("/app/settings")
    fetchMock.mockResolvedValue({
      ok: true,
      arrayBuffer: async () => MINIMAL_ZIP_BYTES.buffer,
    })

    const result = await submitFeedbackDownload({
      note: "App froze on settings",
      context: {
        source: "recovery",
        failureKind: "boot_failed",
      },
      contactMethod: "email",
      contactValue: "user@example.com",
    })

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/feedback/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        note:
          "App froze on settings\n\n[contact] method=email value=user@example.com",
        issue_url: null,
        ui_error_name: "boot_failed",
        ui_error_route: "/app/settings",
      }),
    })
    expect(result).toEqual({ attachmentKind: "zip" })
    expect(createdLink.download).toBe(FEEDBACK_JOURNAL_ZIP_FILENAME)
    expect(createObjectUrlMock).toHaveBeenCalledTimes(1)
    expect(clickMock).toHaveBeenCalledTimes(1)
    expect(assignMock).toHaveBeenCalledTimes(1)
    expect(assignMock.mock.calls[0][0]).toContain("node_journal.zip")
    expect(assignMock.mock.calls[0][0]).toContain("App%20froze%20on%20settings")
  })

  it("sends navbar export request body with ui_error_route", async () => {
    stubWindowPathname("/app/settings")
    fetchMock.mockResolvedValue({
      ok: true,
      arrayBuffer: async () => MINIMAL_ZIP_BYTES.buffer,
    })

    await submitFeedbackDownload({
      note: "Navbar feedback",
      context: { source: "navbar" },
    })

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/feedback/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        note: "[ui_context] source=navbar\n\nNavbar feedback",
        issue_url: null,
        ui_error_name: null,
        ui_error_route: "/app/settings",
      }),
    })
  })

  it("sends route error context on export request fields", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      arrayBuffer: async () => MINIMAL_ZIP_BYTES.buffer,
    })

    await submitFeedbackDownload({
      context: { source: "route_error", routePath: "/app/x" },
    })

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/feedback/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        note: null,
        issue_url: null,
        ui_error_name: "route_error",
        ui_error_route: "/app/x",
      }),
    })
  })

  it("downloads recovery fallback json when export fails without preview", async () => {
    stubWindowPathname("/app/insecure")
    fetchMock.mockRejectedValue(new Error("network error"))

    const result = await submitFeedbackDownload({
      note: "Recovery note",
      context: {
        source: "recovery",
        failureKind: "auth_broken",
      },
    })

    expect(result.attachmentKind).toBe("json")
    if (result.attachmentKind === "json") {
      expect(result.envelope.install_id).toBe("recovery-client-fallback")
      expect(result.envelope.note).toBe("Recovery note")
      expect(result.envelope.ui_error_name).toBe("auth_broken")
      expect(result.envelope.ui_error_route).toBe("/app/insecure")
    }
    expect(createdLink.download).toBe(FEEDBACK_JOURNAL_JSON_FILENAME)
    expect(createObjectUrlMock).toHaveBeenCalledTimes(1)
    expect(assignMock.mock.calls[0][0]).toContain("node_journal.json")
  })

  it("downloads preview json fallback when export fails for navbar", async () => {
    fetchMock.mockRejectedValue(new Error("network error"))
    const previewEnvelope = {
      install_id: "preview-install",
      app_version: "1.0.0",
      onboarding_started_at: null,
      onboarding_complete: true,
      journey_summary: {},
      events: [{ event: "wallet_setup_succeeded" }],
      uploaded: false,
      ready: true,
      event_count: 1,
    } as FeedbackUploadEnvelope

    const result = await submitFeedbackDownload({
      note: "Navbar feedback",
      context: { source: "navbar" },
      previewUploadEnvelope: previewEnvelope,
    })

    expect(result.attachmentKind).toBe("json")
    if (result.attachmentKind === "json") {
      expect(result.envelope.install_id).toBe("preview-install")
      expect(result.envelope.note).toBe(
        "[ui_context] source=navbar\n\nNavbar feedback",
      )
      expect(result.envelope.ui_error_name).toBeNull()
      expect(result.envelope.ui_error_route).toBe("/app")
      expect(result.envelope.event_count).toBe(1)
    }
    expect(assignMock.mock.calls[0][0]).toContain("node_journal.json")
  })
})
