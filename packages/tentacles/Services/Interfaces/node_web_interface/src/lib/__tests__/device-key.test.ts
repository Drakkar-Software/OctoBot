import "fake-indexeddb/auto"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import {
  clearClientKeys,
  clearPassword,
  derivePassphraseKey,
  hasStoredClientKeys,
  loadClientKeys,
  loadPassword,
  saveClientKeys,
  savePassword,
} from "../device-key"

// --- localStorage mock ---

const localStorageStore: Record<string, string> = {}

const localStorageMock = {
  getItem: (key: string) => localStorageStore[key] ?? null,
  setItem: (key: string, value: string) => { localStorageStore[key] = value },
  removeItem: (key: string) => { delete localStorageStore[key] },
  clear: () => { Object.keys(localStorageStore).forEach((k) => delete localStorageStore[k]) },
}

vi.stubGlobal("localStorage", localStorageMock)

// --- helpers ---

function setWallet(address: string) {
  localStorageMock.setItem("auth_username", address)
}

function clearWallet() {
  localStorageMock.removeItem("auth_username")
}

const WALLET_A = "0xaaaa000000000000000000000000000000000001"
const WALLET_B = "0xbbbb000000000000000000000000000000000002"
const PASSPHRASE_A = "passphrase-wallet-a"
const PASSPHRASE_B = "passphrase-wallet-b"

const SAMPLE_KEYS = { ecdsa_private: "ecdsa-priv-key", rsa_private: "rsa-priv-key" }

async function clearIDB(): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const req = indexedDB.open("octobot_device", 1)
    req.onupgradeneeded = () => {
      req.result.createObjectStore("secure_storage")
    }
    req.onsuccess = () => {
      const db = req.result
      const tx = db.transaction("secure_storage", "readwrite")
      const clearReq = tx.objectStore("secure_storage").clear()
      clearReq.onsuccess = () => {
        db.close()
        resolve()
      }
      clearReq.onerror = () => {
        db.close()
        reject(clearReq.error)
      }
    }
    req.onerror = () => reject(req.error)
  })
}

beforeEach(async () => {
  localStorageMock.clear()
  await clearIDB()
})

afterEach(async () => {
  localStorageMock.clear()
  await clearIDB()
})

// ─── derivePassphraseKey ────────────────────────────────────────────────────

describe("derivePassphraseKey", () => {
  it("returns a CryptoKey usable for AES-GCM", async () => {
    const key = await derivePassphraseKey(PASSPHRASE_A, WALLET_A)
    expect(key.type).toBe("secret")
    expect(key.algorithm.name).toBe("AES-GCM")
  })

  it("is deterministic — same passphrase+address produces a key that decrypts its own ciphertext", async () => {
    const key1 = await derivePassphraseKey(PASSPHRASE_A, WALLET_A)
    const key2 = await derivePassphraseKey(PASSPHRASE_A, WALLET_A)

    const iv = crypto.getRandomValues(new Uint8Array(12))
    const encoded = new TextEncoder().encode("test")
    const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key1, encoded)
    const plaintext = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key2, ciphertext)
    expect(new TextDecoder().decode(plaintext)).toBe("test")
  })

  it("different passphrase → different key (cannot cross-decrypt)", async () => {
    const keyA = await derivePassphraseKey(PASSPHRASE_A, WALLET_A)
    const keyB = await derivePassphraseKey(PASSPHRASE_B, WALLET_A)

    const iv = crypto.getRandomValues(new Uint8Array(12))
    const ciphertext = await crypto.subtle.encrypt(
      { name: "AES-GCM", iv },
      keyA,
      new TextEncoder().encode("secret"),
    )
    await expect(
      crypto.subtle.decrypt({ name: "AES-GCM", iv }, keyB, ciphertext),
    ).rejects.toThrow()
  })

  it("different address → different key (cannot cross-decrypt)", async () => {
    const keyA = await derivePassphraseKey(PASSPHRASE_A, WALLET_A)
    const keyB = await derivePassphraseKey(PASSPHRASE_A, WALLET_B)

    const iv = crypto.getRandomValues(new Uint8Array(12))
    const ciphertext = await crypto.subtle.encrypt(
      { name: "AES-GCM", iv },
      keyA,
      new TextEncoder().encode("secret"),
    )
    await expect(
      crypto.subtle.decrypt({ name: "AES-GCM", iv }, keyB, ciphertext),
    ).rejects.toThrow()
  })

  it("address comparison is case-insensitive", async () => {
    const keyLower = await derivePassphraseKey(PASSPHRASE_A, WALLET_A.toLowerCase())
    const keyUpper = await derivePassphraseKey(PASSPHRASE_A, WALLET_A.toUpperCase())

    const iv = crypto.getRandomValues(new Uint8Array(12))
    const ciphertext = await crypto.subtle.encrypt(
      { name: "AES-GCM", iv },
      keyLower,
      new TextEncoder().encode("case test"),
    )
    const plaintext = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, keyUpper, ciphertext)
    expect(new TextDecoder().decode(plaintext)).toBe("case test")
  })
})

// ─── saveClientKeys / loadClientKeys ───────────────────────────────────────

describe("saveClientKeys / loadClientKeys", () => {
  it("saves and loads keys for the active wallet", async () => {
    setWallet(WALLET_A)
    await savePassword(PASSPHRASE_A)

    await saveClientKeys(SAMPLE_KEYS)
    const loaded = await loadClientKeys()

    expect(loaded).toEqual(SAMPLE_KEYS)
  })

  it("returns null when no wallet is active", async () => {
    clearWallet()
    expect(await loadClientKeys()).toBeNull()
  })

  it("returns null when no passphrase is stored", async () => {
    setWallet(WALLET_A)
    await clearPassword()
    expect(await loadClientKeys()).toBeNull()
  })

  it("throws when saving with no active session", async () => {
    clearWallet()
    await expect(saveClientKeys(SAMPLE_KEYS)).rejects.toThrow("No active wallet session")
  })

  it("throws when saving with no passphrase stored", async () => {
    setWallet(WALLET_A)
    await clearPassword()
    await expect(saveClientKeys(SAMPLE_KEYS)).rejects.toThrow("No active wallet session")
  })
})

// ─── per-wallet isolation ──────────────────────────────────────────────────

describe("per-wallet isolation", () => {
  it("wallet A keys are not visible to wallet B", async () => {
    setWallet(WALLET_A)
    await savePassword(PASSPHRASE_A)
    await saveClientKeys(SAMPLE_KEYS)

    // Switch to wallet B
    setWallet(WALLET_B)
    await savePassword(PASSPHRASE_B)

    expect(await loadClientKeys()).toBeNull()
  })

  it("wallet B keys do not overwrite wallet A keys", async () => {
    // Save keys for A
    setWallet(WALLET_A)
    await savePassword(PASSPHRASE_A)
    await saveClientKeys(SAMPLE_KEYS)

    // Save different keys for B
    const keysB = { ecdsa_private: "ecdsa-b", rsa_private: "rsa-b" }
    setWallet(WALLET_B)
    await savePassword(PASSPHRASE_B)
    await saveClientKeys(keysB)

    // Switch back to A — original keys intact
    setWallet(WALLET_A)
    await savePassword(PASSPHRASE_A)
    expect(await loadClientKeys()).toEqual(SAMPLE_KEYS)

    // Verify B still has its own keys
    setWallet(WALLET_B)
    await savePassword(PASSPHRASE_B)
    expect(await loadClientKeys()).toEqual(keysB)
  })

  it("wrong passphrase for the same address returns null", async () => {
    setWallet(WALLET_A)
    await savePassword(PASSPHRASE_A)
    await saveClientKeys(SAMPLE_KEYS)

    // Same address but wrong passphrase
    await savePassword("wrong-passphrase")
    expect(await loadClientKeys()).toBeNull()
  })
})

// ─── clearClientKeys ───────────────────────────────────────────────────────

describe("clearClientKeys", () => {
  it("removes keys for the active wallet", async () => {
    setWallet(WALLET_A)
    await savePassword(PASSPHRASE_A)
    await saveClientKeys(SAMPLE_KEYS)

    await clearClientKeys()
    expect(await loadClientKeys()).toBeNull()
  })

  it("does not affect keys for another wallet", async () => {
    // Save for A and B
    setWallet(WALLET_A)
    await savePassword(PASSPHRASE_A)
    await saveClientKeys(SAMPLE_KEYS)

    setWallet(WALLET_B)
    await savePassword(PASSPHRASE_B)
    await saveClientKeys(SAMPLE_KEYS)

    // Clear B
    await clearClientKeys()
    expect(await loadClientKeys()).toBeNull()

    // A should still have keys
    setWallet(WALLET_A)
    await savePassword(PASSPHRASE_A)
    expect(await loadClientKeys()).toEqual(SAMPLE_KEYS)
  })

  it("is a no-op when no wallet is active", async () => {
    clearWallet()
    await expect(clearClientKeys()).resolves.toBeUndefined()
  })
})

// ─── hasStoredClientKeys ───────────────────────────────────────────────────

describe("hasStoredClientKeys", () => {
  it("returns false when no keys are stored", async () => {
    setWallet(WALLET_A)
    await savePassword(PASSPHRASE_A)
    expect(await hasStoredClientKeys()).toBe(false)
  })

  it("returns true after saving valid keys", async () => {
    setWallet(WALLET_A)
    await savePassword(PASSPHRASE_A)
    await saveClientKeys(SAMPLE_KEYS)
    expect(await hasStoredClientKeys()).toBe(true)
  })

  it("returns false after clearing keys", async () => {
    setWallet(WALLET_A)
    await savePassword(PASSPHRASE_A)
    await saveClientKeys(SAMPLE_KEYS)
    await clearClientKeys()
    expect(await hasStoredClientKeys()).toBe(false)
  })

  it("returns false when no wallet is active", async () => {
    clearWallet()
    expect(await hasStoredClientKeys()).toBe(false)
  })
})

// ─── wallet switch restores keys ───────────────────────────────────────────

describe("wallet switch restores keys on login", () => {
  it("switching back to a wallet restores its keys when passphrase matches", async () => {
    // Login as A, save keys
    setWallet(WALLET_A)
    await savePassword(PASSPHRASE_A)
    await saveClientKeys(SAMPLE_KEYS)

    // Logout (clearAuth clears auth_username + password)
    clearWallet()
    await clearPassword()

    // Login as B, save different keys
    const keysB = { ecdsa_private: "ecdsa-b", rsa_private: "rsa-b" }
    setWallet(WALLET_B)
    await savePassword(PASSPHRASE_B)
    await saveClientKeys(keysB)

    // Switch back to A
    setWallet(WALLET_A)
    await savePassword(PASSPHRASE_A)
    expect(await loadClientKeys()).toEqual(SAMPLE_KEYS)
  })
})
