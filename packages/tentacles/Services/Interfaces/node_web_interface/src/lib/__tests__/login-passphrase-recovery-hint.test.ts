import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import {
  LOGIN_PASSPHRASE_RECOVERY_SUCCESS_STORAGE_KEY,
  LOGIN_PASSPHRASE_RECOVERY_SUCCESS_TOAST_DESCRIPTION,
  LOGIN_PASSPHRASE_RECOVERY_SUCCESS_TOAST_TITLE,
  consumeLoginPassphraseRecoverySuccessHint,
  markLoginPassphraseRecoverySuccess,
  showLoginPassphraseRecoverySuccessToast,
} from "@/lib/login-passphrase-recovery-hint"

const toastSuccess = vi.fn()

vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
  },
}))

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

describe("login-passphrase-recovery-hint", () => {
  beforeEach(() => {
    sessionStorageMock.clear()
  })

  afterEach(() => {
    toastSuccess.mockClear()
  })

  it("marks and consumes the session hint once", () => {
    expect(consumeLoginPassphraseRecoverySuccessHint()).toBe(false)
    markLoginPassphraseRecoverySuccess()
    expect(
      sessionStorage.getItem(LOGIN_PASSPHRASE_RECOVERY_SUCCESS_STORAGE_KEY),
    ).toBe("1")
    expect(consumeLoginPassphraseRecoverySuccessHint()).toBe(true)
    expect(consumeLoginPassphraseRecoverySuccessHint()).toBe(false)
  })

  it("shows the passphrase updated success toast", () => {
    showLoginPassphraseRecoverySuccessToast()
    expect(toastSuccess).toHaveBeenCalledWith(
      LOGIN_PASSPHRASE_RECOVERY_SUCCESS_TOAST_TITLE,
      {
        description: LOGIN_PASSPHRASE_RECOVERY_SUCCESS_TOAST_DESCRIPTION,
      },
    )
  })
})
