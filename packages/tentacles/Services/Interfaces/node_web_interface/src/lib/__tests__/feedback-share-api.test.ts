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

  it("uploads composed note with contact details and downloads envelope", async () => {
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
          "[ui_context] source=recovery failure_kind=boot_failed\n\nApp froze on settings\n\n[contact] method=email value=user@example.com",
        issue_url: null,
      },
    })
    expect(createObjectUrlMock).toHaveBeenCalledTimes(1)
    expect(clickMock).toHaveBeenCalledTimes(1)
  })

  it("downloads recovery fallback when upload fails", async () => {
    mockedUploadFeedback.mockRejectedValue(new Error("network error"))

    const envelope = await submitFeedbackDownload({
      note: "Recovery note",
      context: {
        source: "recovery",
        failureKind: "auth_broken",
      },
    })

    expect(envelope.install_id).toBe("recovery-client-fallback")
    expect(envelope.note).toContain("recovery failure_kind=auth_broken")
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
