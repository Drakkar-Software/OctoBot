import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/client", () => ({
  FeedbackService: {
    getFeedbackPreview: vi.fn(),
    uploadFeedback: vi.fn(),
  },
}))

import { FeedbackService } from "@/client"
import { submitFeedbackDownload } from "@/lib/feedback-share"

const mockedUploadFeedback = vi.mocked(FeedbackService.uploadFeedback)

function stubWindowPathname(pathname: string) {
  vi.stubGlobal("window", {
    location: { pathname },
  })
}

describe("submitFeedbackDownload", () => {
  const createObjectUrlMock = vi.fn(() => "blob:feedback")
  const revokeObjectUrlMock = vi.fn()
  const clickMock = vi.fn()

  beforeEach(() => {
    mockedUploadFeedback.mockReset()
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

  it("uploads note, ui_error_name, and contact without context in note", async () => {
    stubWindowPathname("/app/settings")
    const uploadEnvelope = {
      install_id: "install-1",
      event_count: 2,
      uploaded: false,
    }
    mockedUploadFeedback.mockResolvedValue(uploadEnvelope as never)

    await submitFeedbackDownload({
      note: "App froze on settings",
      context: {
        source: "recovery",
        failureKind: "boot_failed",
      },
      contactMethod: "email",
      contactValue: "user@example.com",
    })

    expect(mockedUploadFeedback).toHaveBeenCalledWith({
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
  })

  it("uploads ui_error_route from current page for navbar feedback", async () => {
    stubWindowPathname("/app/settings")
    mockedUploadFeedback.mockResolvedValue({ install_id: "x" } as never)

    await submitFeedbackDownload({
      note: "Navbar feedback",
      context: { source: "navbar" },
    })

    expect(mockedUploadFeedback).toHaveBeenCalledWith({
      requestBody: {
        note: "[ui_context] source=navbar\n\nNavbar feedback",
        issue_url: null,
        ui_error_name: null,
        ui_error_route: "/app/settings",
      },
    })
  })

  it("uploads route error context on envelope request fields", async () => {
    mockedUploadFeedback.mockResolvedValue({ install_id: "x" } as never)

    await submitFeedbackDownload({
      context: { source: "route_error", routePath: "/app/x" },
    })

    expect(mockedUploadFeedback).toHaveBeenCalledWith({
      requestBody: {
        note: null,
        issue_url: null,
        ui_error_name: "route_error",
        ui_error_route: "/app/x",
      },
    })
  })

  it("downloads recovery fallback when upload fails", async () => {
    stubWindowPathname("/app/insecure")
    mockedUploadFeedback.mockRejectedValue(new Error("network error"))

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
  })

  it("rethrows upload errors for non-recovery context", async () => {
    mockedUploadFeedback.mockRejectedValue(new Error("network error"))

    await expect(
      submitFeedbackDownload({
        note: "Navbar feedback",
        context: { source: "navbar" },
      }),
    ).rejects.toThrow("network error")
    expect(createObjectUrlMock).not.toHaveBeenCalled()
  })
})
