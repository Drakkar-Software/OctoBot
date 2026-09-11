import { describe, expect, it, vi } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"

import {
  handleShellRenderError,
  ShellErrorFallback,
} from "@/bootstrap-app"
import { RecoveryScreen } from "@/components/Common/RecoveryScreen"

const mocks = vi.hoisted(() => ({
  reportShellFatalError: vi.fn(),
}))

vi.mock("@/lib/shell-error-reporting", () => ({
  reportShellFatalError: mocks.reportShellFatalError,
  reportBootFailed: vi.fn(),
  reportAuthStateBroken: vi.fn(),
}))

vi.mock("@/components/Common/ShareFeedbackButton", () => ({
  ShareFeedbackButton: () => null,
}))

describe("shell error boundary wiring", () => {
  it("journals shell render errors through reportShellFatalError", () => {
    handleShellRenderError(new Error("render boom"))
    expect(mocks.reportShellFatalError).toHaveBeenCalledOnce()
    expect(mocks.reportShellFatalError).toHaveBeenCalledWith(
      expect.objectContaining({ message: "render boom" }),
    )
  })

  it("uses RecoveryScreen as the fatal render fallback", () => {
    const fallbackMarkup = renderToStaticMarkup(<ShellErrorFallback />)
    const recoveryMarkup = renderToStaticMarkup(
      <RecoveryScreen failureKind="fatal_render" />,
    )
    expect(fallbackMarkup).toBe(recoveryMarkup)
    expect(fallbackMarkup).toContain("Reset local browser data")
  })
})
