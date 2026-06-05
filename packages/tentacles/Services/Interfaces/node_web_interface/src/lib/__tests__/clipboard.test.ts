import { beforeEach, describe, expect, it, vi } from "vitest"

import { copyTextToClipboard } from "@/lib/clipboard"

const toastSuccess = vi.fn()

vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
  },
}))

describe("copyTextToClipboard", () => {
  beforeEach(() => {
    toastSuccess.mockClear()
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    })
  })

  it("writes text to the clipboard and shows a toast", async () => {
    copyTextToClipboard("hello", "Sample text")
    await Promise.resolve()
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("hello")
    expect(toastSuccess).toHaveBeenCalledWith("Copied to clipboard", {
      description: "Sample text",
    })
  })
})
