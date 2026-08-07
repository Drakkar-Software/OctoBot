import { describe, expect, it } from "vitest"
import {
  loadStoredPrivateKey,
  persistPrivateKey,
  resolveInitialPrivateKey,
  safeLocalStorage,
  WALLET_KEY_STORAGE_KEY,
} from "../src/components/demo/lib/walletKeyStorage"

// Regression coverage for: the demo used to call
// `useState(() => generateRandomPrivateKey())` with no read from storage, so
// every page reload silently swapped the wallet identity — the exact bug
// report this fixed ("the previous private key doesn't work anymore").

function fakeStorage(initial: Record<string, string> = {}) {
  const store = new Map(Object.entries(initial))
  return {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => {
      store.set(key, value)
    },
    _store: store,
  }
}

const REAL_KEY =
  "0x1111111111111111111111111111111111111111111111111111111111aa"

describe("loadStoredPrivateKey", () => {
  it("returns a previously persisted key", () => {
    const storage = fakeStorage({ [WALLET_KEY_STORAGE_KEY]: REAL_KEY })
    expect(loadStoredPrivateKey(storage)).toBe(REAL_KEY)
  })

  it("returns null when nothing was ever persisted", () => {
    const storage = fakeStorage()
    expect(loadStoredPrivateKey(storage)).toBeNull()
  })

  it("returns null (not throw) when storage.getItem throws", () => {
    const storage = {
      getItem: () => {
        throw new Error("storage disabled")
      },
    }
    expect(loadStoredPrivateKey(storage)).toBeNull()
  })
})

describe("persistPrivateKey", () => {
  it("writes the key under the shared storage key", () => {
    const storage = fakeStorage()
    persistPrivateKey(storage, REAL_KEY)
    expect(storage._store.get(WALLET_KEY_STORAGE_KEY)).toBe(REAL_KEY)
  })

  it("does not throw when storage.setItem throws (private browsing / quota)", () => {
    const storage = {
      setItem: () => {
        throw new Error("quota exceeded")
      },
    }
    expect(() => persistPrivateKey(storage, REAL_KEY)).not.toThrow()
  })
})

describe("resolveInitialPrivateKey — the actual regression", () => {
  it("reuses a persisted key across a simulated reload, instead of generating a new one", () => {
    const storage = fakeStorage({ [WALLET_KEY_STORAGE_KEY]: REAL_KEY })
    expect(resolveInitialPrivateKey(storage)).toBe(REAL_KEY)
  })

  it("generates a fresh key only when nothing was persisted yet", () => {
    const storage = fakeStorage()
    const key = resolveInitialPrivateKey(storage)
    expect(key).toMatch(/^0x[0-9a-f]{64}$/)
  })

  it("two resolutions against the SAME persisted storage return the SAME key (the reload contract)", () => {
    const storage = fakeStorage({ [WALLET_KEY_STORAGE_KEY]: REAL_KEY })
    const first = resolveInitialPrivateKey(storage)
    const second = resolveInitialPrivateKey(storage)
    expect(first).toBe(REAL_KEY)
    expect(second).toBe(REAL_KEY)
  })
})

describe("safeLocalStorage", () => {
  // This suite runs under plain Node (no DOM environment configured), where
  // `localStorage` isn't a global — exactly the "unavailable" case this
  // function exists to handle safely. The contract under test is "never
  // throws, degrades to null" — not "a browser is present".
  it("never throws even when localStorage isn't available, and returns null or a real Storage", () => {
    let result: Storage | null | undefined
    expect(() => {
      result = safeLocalStorage()
    }).not.toThrow()
    expect(result === null || typeof result?.getItem === "function").toBe(true)
  })
})
