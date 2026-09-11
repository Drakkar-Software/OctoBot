import { beforeEach, describe, expect, it, vi } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"

import {
  confirmAndResetLocalBrowserData,
  RecoveryScreen,
} from "@/components/Common/RecoveryScreen"

const mocks = vi.hoisted(() => ({
  resetClientStorage: vi.fn().mockResolvedValue(undefined),
}))

vi.mock("@/lib/client-storage-reset", () => ({
  resetClientStorage: mocks.resetClientStorage,
}))

vi.mock("@/components/Common/ShareFeedbackButton", () => ({
  ShareFeedbackButton: () => null,
}))

describe("RecoveryScreen", () => {
  beforeEach(() => {
    mocks.resetClientStorage.mockClear()
  })

  it("does not reset on mount", () => {
    renderToStaticMarkup(<RecoveryScreen failureKind="boot_failed" />)
    expect(mocks.resetClientStorage).not.toHaveBeenCalled()
  })

  it("does not reset when confirmation is declined", () => {
    confirmAndResetLocalBrowserData(() => false)
    expect(mocks.resetClientStorage).not.toHaveBeenCalled()
  })

  it("resets once when confirmation is accepted", () => {
    confirmAndResetLocalBrowserData(() => true)
    expect(mocks.resetClientStorage).toHaveBeenCalledOnce()
    expect(mocks.resetClientStorage).toHaveBeenCalledWith("manual_recovery")
  })

  it("does not render tier selection controls", () => {
    const markup = renderToStaticMarkup(
      <RecoveryScreen failureKind="auth_broken" />,
    )
    expect(markup).not.toMatch(/<select/i)
    expect(markup).not.toMatch(/type="radio"/i)
    expect(markup).not.toContain("auth_only")
    expect(markup).not.toContain("auth_and_templates")
  })
})
