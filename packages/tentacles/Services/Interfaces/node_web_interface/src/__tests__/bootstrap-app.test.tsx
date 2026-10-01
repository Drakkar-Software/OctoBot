import { beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({
  createRouter: vi.fn(() => ({ id: "router-mock" })),
  isWebCryptoAvailable: vi.fn(() => true),
  probeAuthState: vi.fn(async () => "ok" as const),
  reportInsecureContext: vi.fn(),
  render: vi.fn(),
}))

vi.mock("react-dom/client", () => ({
  createRoot: () => ({
    render: mocks.render,
  }),
}))

vi.mock("@tanstack/react-router", () => ({
  createRouter: mocks.createRouter,
  RouterProvider: () => null,
}))

vi.mock("@/routeTree.gen", () => ({
  routeTree: {},
}))

vi.mock("@/lib/secure-context", () => ({
  isWebCryptoAvailable: mocks.isWebCryptoAvailable,
}))

vi.mock("@/lib/auth-state-probe", () => ({
  probeAuthState: mocks.probeAuthState,
}))

vi.mock("@/lib/shell-error-reporting", () => ({
  reportInsecureContext: mocks.reportInsecureContext,
  reportAuthStateBroken: vi.fn(),
  reportShellFatalError: vi.fn(),
}))

vi.mock("@/lib/device-key", () => ({
  loadPassword: vi.fn(async () => null),
}))

import { bootstrapApp } from "@/bootstrap-app"

describe("bootstrapApp insecure context", () => {
  beforeEach(() => {
    mocks.createRouter.mockClear()
    mocks.isWebCryptoAvailable.mockReturnValue(true)
    mocks.probeAuthState.mockResolvedValue("ok")
    mocks.reportInsecureContext.mockClear()
    mocks.render.mockClear()
    vi.stubGlobal("document", {
      getElementById: vi.fn(() => ({ id: "root" })),
    })
    vi.stubGlobal("window", {
      isSecureContext: false,
      location: { hostname: "192.168.0.1", pathname: "/app", port: "8000" },
    })
  })

  it("renders recovery and skips router when web crypto is unavailable", async () => {
    mocks.isWebCryptoAvailable.mockReturnValue(false)

    await bootstrapApp()

    expect(mocks.reportInsecureContext).toHaveBeenCalledOnce()
    expect(mocks.render).toHaveBeenCalledOnce()
    expect(mocks.createRouter).not.toHaveBeenCalled()
    expect(mocks.probeAuthState).not.toHaveBeenCalled()
  })
})
