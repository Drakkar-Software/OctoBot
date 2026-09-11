import { beforeEach, describe, expect, it, vi } from "vitest"

import {
  AUTH_IS_SUPERUSER_KEY,
  displayName,
  getCachedNavbarDisplayName,
  getStoredIsSuperuser,
  setStoredIsSuperuser,
} from "@/lib/user-menu-display"

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

vi.stubGlobal("localStorage", localStorageMock)

describe("getCachedNavbarDisplayName", () => {
  beforeEach(() => {
    localStorageMock.clear()
  })

  it("returns auth_wallet_name when set", () => {
    localStorageMock.setItem("auth_wallet_name", "groot")

    expect(getCachedNavbarDisplayName()).toBe("groot")
  })

  it("truncates long auth_username when wallet name is missing", () => {
    localStorageMock.setItem(
      "auth_username",
      "0xaaaa000000000000000000000000000000000001",
    )

    expect(getCachedNavbarDisplayName()).toBe("0xaaaa…0001")
  })

  it("returns em dash when no cached name or username", () => {
    expect(getCachedNavbarDisplayName()).toBe("—")
  })
})

describe("getStoredIsSuperuser", () => {
  beforeEach(() => {
    localStorageMock.clear()
  })

  it("returns false when auth_is_superuser is not set", () => {
    expect(getStoredIsSuperuser()).toBe(false)
  })

  it("returns true when auth_is_superuser is true", () => {
    localStorageMock.setItem(AUTH_IS_SUPERUSER_KEY, "true")
    expect(getStoredIsSuperuser()).toBe(true)
  })
})

describe("setStoredIsSuperuser", () => {
  beforeEach(() => {
    localStorageMock.clear()
  })

  it("stores true as auth_is_superuser", () => {
    setStoredIsSuperuser(true)
    expect(localStorageMock.getItem(AUTH_IS_SUPERUSER_KEY)).toBe("true")
  })

  it("removes auth_is_superuser when set to false", () => {
    localStorageMock.setItem(AUTH_IS_SUPERUSER_KEY, "true")
    setStoredIsSuperuser(false)
    expect(localStorageMock.getItem(AUTH_IS_SUPERUSER_KEY)).toBeNull()
  })
})

describe("displayName", () => {
  beforeEach(() => {
    localStorageMock.clear()
  })

  it("prefers server full name over localStorage", () => {
    localStorageMock.setItem("auth_wallet_name", "Stale name")

    expect(displayName("0xabc@node", "Server wallet")).toBe("Server wallet")
  })

  it("falls back to auth_wallet_name from localStorage", () => {
    localStorageMock.setItem("auth_wallet_name", "Main wallet")

    expect(displayName("0xabc@node", null)).toBe("Main wallet")
  })

  it("truncates long email when no name is available", () => {
    expect(
      displayName("0xaaaa000000000000000000000000000000000001", null),
    ).toBe("0xaaaa…0001")
  })

  it("returns short email unchanged when no name is available", () => {
    expect(displayName("short@node", null)).toBe("short@node")
  })

  it("returns em dash when email and names are missing", () => {
    expect(displayName(undefined, null)).toBe("—")
  })
})
