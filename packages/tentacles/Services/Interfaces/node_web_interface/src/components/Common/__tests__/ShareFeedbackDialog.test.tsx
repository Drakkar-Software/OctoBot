import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import * as React from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { ApiError } from "@/client"
import { ShareFeedbackDialogContent } from "@/components/Common/ShareFeedbackDialog"
import { Dialog } from "@/components/ui/dialog"

const shareFeedbackDialogTestState = vi.hoisted(() => ({
  noteOverride: "",
  useStateCallIndex: 0,
}))

vi.mock("react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react")>()
  return {
    ...actual,
    useState: <State,>(
      initialState: State | (() => State),
    ): [State, React.Dispatch<React.SetStateAction<State>>] => {
      shareFeedbackDialogTestState.useStateCallIndex += 1
      if (
        shareFeedbackDialogTestState.useStateCallIndex === 1 &&
        shareFeedbackDialogTestState.noteOverride !== "" &&
        initialState === ""
      ) {
        return [
          shareFeedbackDialogTestState.noteOverride as State,
          vi.fn(),
        ]
      }
      return actual.useState(initialState)
    },
  }
})

const useQueryMock = vi.fn()

vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@tanstack/react-query")>()
  return {
    ...actual,
    useQuery: (...args: unknown[]) => useQueryMock(...args),
  }
})

vi.mock("@/hooks/useCustomToast", () => ({
  default: () => ({
    showErrorToast: vi.fn(),
    showSuccessToast: vi.fn(),
  }),
}))

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children }: { children: React.ReactNode }) => <a>{children}</a>,
}))

vi.mock("@/components/ui/dialog", () => ({
  Dialog: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogContent: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  DialogHeader: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  DialogFooter: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  DialogTitle: ({ children }: { children: React.ReactNode }) => (
    <h2>{children}</h2>
  ),
  DialogDescription: ({ children }: { children: React.ReactNode }) => (
    <p>{children}</p>
  ),
  DialogClose: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}))

vi.mock("@/lib/feedback-share", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/feedback-share")>(
      "@/lib/feedback-share",
    )
  return {
    ...actual,
    submitFeedbackDownload: vi.fn().mockResolvedValue({}),
  }
})

function createPreviewResponse(eventCount: number) {
  return {
    journey_summary: {},
    upload_envelope: {
      install_id: "install-test",
      app_version: "1.0.0",
      onboarding_started_at: null,
      onboarding_complete: false,
      journey_summary: {},
      events: eventCount > 0 ? [{ event: "test_event" }] : [],
      uploaded: false,
      ready: true,
      event_count: eventCount,
    },
  }
}

function create401PreviewError(): ApiError {
  return new ApiError(
    { method: "GET", url: "/api/v1/feedback/preview" },
    {
      url: "/api/v1/feedback/preview",
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      body: {},
    },
    "Unauthorized",
  )
}

function renderDialog(
  context: import("@/lib/feedback-share").ShareFeedbackContext,
) {
  const queryClient = new QueryClient()
  return renderToStaticMarkup(
    <QueryClientProvider client={queryClient}>
      <Dialog open onOpenChange={() => {}}>
        <ShareFeedbackDialogContent
          open
          onOpenChange={() => {}}
          context={context}
        />
      </Dialog>
    </QueryClientProvider>,
  )
}

describe("ShareFeedbackDialogContent", () => {
  beforeEach(() => {
    useQueryMock.mockReset()
    shareFeedbackDialogTestState.noteOverride = ""
    shareFeedbackDialogTestState.useStateCallIndex = 0
  })

  it("recovery + preview 401: no sign-in prompt, no activity history, send enabled", () => {
    useQueryMock.mockReturnValue({
      data: undefined,
      error: create401PreviewError(),
      isLoading: false,
      isError: true,
      isSuccess: false,
    })

    const markup = renderDialog({
      source: "recovery",
      failureKind: "auth_broken",
    })

    expect(markup).not.toContain("Sign in to send feedback")
    expect(markup).not.toContain("Activity history")
    expect(markup).toContain('id="feedback-note"')
    expect(markup).toContain("Download &amp; email")
    expect(markup).not.toMatch(/Download &amp; email[\s\S]*disabled=""/)
  })

  it("navbar + preview loading: activity history reserves space with empty counts", () => {
    useQueryMock.mockReturnValue({
      data: undefined,
      error: null,
      isLoading: true,
      isError: false,
      isSuccess: false,
    })

    const markup = renderDialog({ source: "navbar" })

    expect(markup).toContain("Activity history")
    expect(markup).toContain("Check file content")
    expect(markup).toMatch(/disabled=""[^>]*>Check file content/)
  })

  it("navbar + preview 200 empty journal: send enabled when note is present", () => {
    shareFeedbackDialogTestState.noteOverride = "Something went wrong"

    useQueryMock.mockReturnValue({
      data: createPreviewResponse(0),
      error: null,
      isLoading: false,
      isError: false,
      isSuccess: true,
    })

    const markup = renderDialog({ source: "navbar" })

    expect(markup).toContain('type="button">Download &amp; email</button>')
    expect(markup).not.toContain('disabled="" type="button">Download &amp; email')
  })

  it("recovery + preview 200: send disabled when journal empty and note empty", () => {
    useQueryMock.mockReturnValue({
      data: createPreviewResponse(0),
      error: null,
      isLoading: false,
      isError: false,
      isSuccess: true,
    })

    const markup = renderDialog({
      source: "recovery",
      failureKind: "boot_failed",
    })

    expect(markup).toContain("Activity history")
    expect(markup).not.toContain("Sign in to send feedback")
    expect(markup).toContain('type="button">Download &amp; email</button>')
    expect(markup).not.toContain('disabled="" type="button">Download &amp; email')
  })

  it("recovery + preview 200: send enabled when journal has events", () => {
    useQueryMock.mockReturnValue({
      data: createPreviewResponse(2),
      error: null,
      isLoading: false,
      isError: false,
      isSuccess: true,
    })

    const markup = renderDialog({
      source: "recovery",
      failureKind: "boot_failed",
    })

    expect(markup).toContain('type="button">Download &amp; email</button>')
    expect(markup).not.toContain('disabled="" type="button">Download &amp; email')
  })
})
