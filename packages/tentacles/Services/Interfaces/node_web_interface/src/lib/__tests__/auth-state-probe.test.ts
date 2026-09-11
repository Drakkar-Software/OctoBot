import { beforeEach, describe, expect, it, vi } from "vitest"

import { probeAuthState } from "@/lib/auth-state-probe"

const localStorageStore: Record<string, string> = {}
const localStorageMock = {
  getItem: (key: string) => localStorageStore[key] ?? null,
  setItem: (key: string, value: string) => {
    localStorageStore[key] = value
  },
  removeItem: (key: string) => {
    delete localStorageStore[key]
  },
  clear: () => {
    Object.keys(localStorageStore).forEach((key) => {
      delete localStorageStore[key]
    })
  },
}

const sessionStorageStore: Record<string, string> = {}
const sessionStorageMock = {
  getItem: (key: string) => sessionStorageStore[key] ?? null,
  setItem: (key: string, value: string) => {
    sessionStorageStore[key] = value
  },
  removeItem: (key: string) => {
    delete sessionStorageStore[key]
  },
  clear: () => {
    Object.keys(sessionStorageStore).forEach((key) => {
      delete sessionStorageStore[key]
    })
  },
}

vi.stubGlobal("localStorage", localStorageMock)
vi.stubGlobal("sessionStorage", sessionStorageMock)

const mocks = vi.hoisted(() => ({
  loadPassword: vi.fn(),
}))

vi.mock("@/lib/device-key", () => ({
  loadPassword: mocks.loadPassword,
}))

describe("probeAuthState", () => {
  beforeEach(() => {
    localStorageMock.clear()
    sessionStorageMock.clear()
    mocks.loadPassword.mockReset()
  })

  it("skips probing while setup is in progress", async () => {
    sessionStorageMock.setItem("setup_in_progress", "1")
    localStorageMock.setItem("auth_username", "wallet")
    await expect(probeAuthState()).resolves.toBe("skipped")
    expect(mocks.loadPassword).not.toHaveBeenCalled()
  })

  it("returns ok when no username is stored", async () => {
    await expect(probeAuthState()).resolves.toBe("ok")
    expect(mocks.loadPassword).not.toHaveBeenCalled()
  })

  it("returns ok when username and password are present", async () => {
    localStorageMock.setItem("auth_username", "wallet")
    mocks.loadPassword.mockResolvedValue("secret")
    await expect(probeAuthState()).resolves.toBe("ok")
  })

  it("returns broken when username exists without password", async () => {
    localStorageMock.setItem("auth_username", "wallet")
    mocks.loadPassword.mockResolvedValue(null)
    await expect(probeAuthState()).resolves.toBe("broken")
  })

  it("returns broken when password loading throws", async () => {
    localStorageMock.setItem("auth_username", "wallet")
    mocks.loadPassword.mockRejectedValue(new Error("idb unavailable"))
    await expect(probeAuthState()).resolves.toBe("broken")
  })
})
