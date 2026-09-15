import { beforeEach, describe, expect, it, vi } from "vitest"

import { copyTextToClipboard } from "@/lib/clipboard"

const toastSuccess = vi.fn()
const toastError = vi.fn()

vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

describe("copyTextToClipboard", () => {
  async function flushPromises(): Promise<void> {
    await Promise.resolve()
    await Promise.resolve()
  }

  beforeEach(() => {
    toastSuccess.mockClear()
    toastError.mockClear()
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    })
  })

  it("writes text with the Clipboard API and shows a toast", async () => {
    copyTextToClipboard("hello", "Sample text")
    await flushPromises()
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("hello")
    expect(toastSuccess).toHaveBeenCalledWith("Copied to clipboard", {
      description: "Sample text",
      classNames: {
        description: "font-mono text-xs break-all",
      },
    })
    expect(toastError).not.toHaveBeenCalled()
  })

  it("uses execCommand when the Clipboard API is unavailable", async () => {
    Object.assign(navigator, { clipboard: undefined })
    const execCommandMock = vi.fn(() => true)
    vi.stubGlobal("document", {
      createElement: () => ({
        value: "",
        style: {},
        setAttribute: vi.fn(),
        select: vi.fn(),
      }),
      body: {
        appendChild: vi.fn(),
        removeChild: vi.fn(),
      },
      execCommand: execCommandMock,
    })

    copyTextToClipboard("tailscale up", "tailscale up")
    await flushPromises()

    expect(execCommandMock).toHaveBeenCalledWith("copy")
    expect(toastSuccess).toHaveBeenCalledWith(
      "Copied to clipboard",
      expect.objectContaining({ description: "tailscale up" }),
    )
    expect(toastError).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
  })

  it("shows an error toast when copy fails", async () => {
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockRejectedValue(new Error("denied")),
      },
    })
    vi.stubGlobal("document", {
      createElement: () => ({
        value: "",
        style: {},
        setAttribute: vi.fn(),
        select: vi.fn(),
      }),
      body: {
        appendChild: vi.fn(),
        removeChild: vi.fn(),
      },
      execCommand: vi.fn(() => false),
    })

    copyTextToClipboard("hello", "hello")
    await flushPromises()

    expect(toastSuccess).not.toHaveBeenCalled()
    expect(toastError).toHaveBeenCalledWith(
      "Could not copy to clipboard",
      expect.objectContaining({
        description: expect.stringContaining("manually"),
      }),
    )
    vi.unstubAllGlobals()
  })
})
