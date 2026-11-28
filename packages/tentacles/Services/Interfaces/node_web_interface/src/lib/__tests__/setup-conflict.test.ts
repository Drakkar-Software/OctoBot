import { beforeEach, describe, expect, it, vi } from "vitest"

import {
  consumeNodeAlreadyInitializedHint,
  isSetupAlreadyConfiguredConflict,
  LOGIN_NODE_ALREADY_INITIALIZED_STORAGE_KEY,
  markNodeAlreadyInitialized,
  NODE_ALREADY_INITIALIZED_MESSAGE,
} from "@/lib/setup-conflict"

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

vi.stubGlobal("sessionStorage", sessionStorageMock)

describe("setup-conflict hints", () => {
  beforeEach(() => {
    sessionStorageMock.clear()
  })

  it("exposes stable already-initialized copy", () => {
    expect(NODE_ALREADY_INITIALIZED_MESSAGE).toContain("already been initialized")
  })

  it("detects setup conflict by HTTP status only", () => {
    expect(isSetupAlreadyConfiguredConflict(409)).toBe(true)
    expect(isSetupAlreadyConfiguredConflict(400)).toBe(false)
    expect(isSetupAlreadyConfiguredConflict(undefined)).toBe(false)
  })

  it("mark then consume returns true once", () => {
    markNodeAlreadyInitialized()
    expect(sessionStorage.getItem(LOGIN_NODE_ALREADY_INITIALIZED_STORAGE_KEY)).toBe(
      "1",
    )
    expect(consumeNodeAlreadyInitializedHint()).toBe(true)
    expect(consumeNodeAlreadyInitializedHint()).toBe(false)
  })
})