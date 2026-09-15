import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
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
  ShareFeedbackButton: () => <span data-testid="share-feedback-stub" />,
}))

vi.mock("@/components/Common/TailscaleRemoteAccessDialog", () => ({
  TailscaleRemoteAccessDialog: () => null,
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

  it("insecure_context omits reset and reload, shows Tailscale setup", () => {
    const markup = renderToStaticMarkup(
      <RecoveryScreen failureKind="insecure_context" />,
    )
    expect(markup).not.toContain("Reset local browser data")
    expect(markup).not.toContain("Reload page")
    expect(markup).toContain("Secure context required")
    expect(markup).toContain("Set up remote access")
    expect(markup).not.toContain("Set up remote access (Tailscale)")
    expect(markup).toContain("Option 1: On this computer (local)")
    expect(markup).toContain("Option 2: From another device (remote)")
    expect(markup).toContain("computer or server")
    expect(markup).toContain("sensitive information")
    expect(markup).toContain("127.0.0.1")
    expect(markup).toContain("Tailscale: a")
    expect(markup).toContain("share-feedback-stub")
    expect(markup).toContain('data-testid="insecure-context-option-remote"')
    expect(markup).toContain('data-testid="recovery-insecure-share-feedback"')
    expect(markup.toLowerCase()).not.toContain("saved data")
    expect(markup.toLowerCase()).not.toContain("local data is fine")
  })
})

describe("RecoveryScreen insecure_context loopback link", () => {
  const originalWindow = globalThis.window

  beforeEach(() => {
    vi.stubGlobal("window", {
      ...originalWindow,
      location: {
        href: "http://192.168.1.50:8000/app/setup?x=1",
        port: "8000",
      },
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("renders clickable 127.0.0.1 link preserving path", () => {
    const markup = renderToStaticMarkup(
      <RecoveryScreen failureKind="insecure_context" />,
    )
    expect(markup).toContain('href="http://127.0.0.1:8000/app/setup?x=1"')
    expect(markup).toContain("http://192.168.1.50:8000/app/setup?x=1")
    expect(markup).toContain("The address in your address bar right now (")
  })
})
