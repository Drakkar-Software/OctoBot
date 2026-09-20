import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import {
  consumeLoginPassphraseRecoveredHint,
  LOGIN_PASSPHRASE_RECOVERED_STORAGE_KEY,
  markLoginPassphraseRecovered,
} from "@/lib/login-passphrase-recovered-hint"

describe("login-passphrase-recovered-hint", () => {
  beforeEach(() => {
    const store = new Map<string, string>()
    vi.stubGlobal("sessionStorage", {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => {
        store.set(key, value)
      },
      removeItem: (key: string) => {
        store.delete(key)
      },
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("consumes the hint once", () => {
    markLoginPassphraseRecovered()
    expect(consumeLoginPassphraseRecoveredHint()).toBe(true)
    expect(consumeLoginPassphraseRecoveredHint()).toBe(false)
  })
})
