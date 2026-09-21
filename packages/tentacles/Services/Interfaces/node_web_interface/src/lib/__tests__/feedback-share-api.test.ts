import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/client", () => ({
  FeedbackService: {
    getFeedbackPreview: vi.fn(),
    exportFeedback: vi.fn(),
  },
}))

import { FeedbackService } from "@/client"
import { submitFeedbackDownload } from "@/lib/feedback-share"

const mockedExportFeedback = vi.mocked(FeedbackService.exportFeedback)
const assignMock = vi.fn()

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
  beforeEach(() => {
    mockedExportFeedback.mockReset()
    createObjectUrlMock.mockClear()
    revokeObjectUrlMock.mockClear()
    clickMock.mockClear()
    assignMock.mockClear()
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

  it("exports note, ui_error_name, and contact without context in note", async () => {
    stubWindowPathname("/app/settings")
    const exportEnvelope = {
      install_id: "install-1",
      event_count: 2,
      uploaded: false,
    }
    mockedExportFeedback.mockResolvedValue(exportEnvelope as never)

    await submitFeedbackDownload({
      note: "App froze on settings",
      context: {
        source: "recovery",
        failureKind: "boot_failed",
      },
      contactMethod: "email",
      contactValue: "user@example.com",
    })

    expect(mockedExportFeedback).toHaveBeenCalledWith({
      requestBody: {
        note:
          "App froze on settings\n\n[contact] method=email value=user@example.com",
        issue_url: null,
        ui_error_name: "boot_failed",
        ui_error_route: "/app/settings",
      },
    })
    expect(createObjectUrlMock).toHaveBeenCalledTimes(1)
    expect(clickMock).toHaveBeenCalledTimes(1)
    expect(assignMock).toHaveBeenCalledTimes(1)
    expect(assignMock.mock.calls[0][0]).toContain("mailto:contact@octobot.cloud")
    expect(assignMock.mock.calls[0][0]).toContain("App+froze+on+settings")
    expect(assignMock.mock.calls[0][0]).not.toContain("install-1")
  })

  it("exports ui_error_route from current page for navbar feedback", async () => {
    stubWindowPathname("/app/settings")
    mockedExportFeedback.mockResolvedValue({ install_id: "x" } as never)

    await submitFeedbackDownload({
      note: "Navbar feedback",
      context: { source: "navbar" },
    })

    expect(mockedExportFeedback).toHaveBeenCalledWith({
      requestBody: {
        note: "[ui_context] source=navbar\n\nNavbar feedback",
        issue_url: null,
        ui_error_name: null,
        ui_error_route: "/app/settings",
      },
    })
  })

  it("exports route error context on envelope request fields", async () => {
    mockedExportFeedback.mockResolvedValue({ install_id: "x" } as never)

    await submitFeedbackDownload({
      context: { source: "route_error", routePath: "/app/x" },
    })

    expect(mockedExportFeedback).toHaveBeenCalledWith({
      requestBody: {
        note: null,
        issue_url: null,
        ui_error_name: "route_error",
        ui_error_route: "/app/x",
      },
    })
  })

  it("downloads recovery fallback when export fails", async () => {
    stubWindowPathname("/app/insecure")
    mockedExportFeedback.mockRejectedValue(new Error("network error"))

    const envelope = await submitFeedbackDownload({
      note: "Recovery note",
      context: {
        source: "recovery",
        failureKind: "auth_broken",
      },
    })

    expect(envelope.install_id).toBe("recovery-client-fallback")
    expect(envelope.note).toBe("Recovery note")
    expect(envelope.ui_error_name).toBe("auth_broken")
    expect(envelope.ui_error_route).toBe("/app/insecure")
    expect(createObjectUrlMock).toHaveBeenCalledTimes(1)
    expect(clickMock).toHaveBeenCalledTimes(1)
    expect(assignMock).toHaveBeenCalledTimes(1)
  })

  it("rethrows export errors for non-recovery context", async () => {
    mockedExportFeedback.mockRejectedValue(new Error("network error"))

    await expect(
      submitFeedbackDownload({
        note: "Navbar feedback",
        context: { source: "navbar" },
      }),
    ).rejects.toThrow("network error")
    expect(createObjectUrlMock).not.toHaveBeenCalled()
    expect(assignMock).not.toHaveBeenCalled()
  })
})
