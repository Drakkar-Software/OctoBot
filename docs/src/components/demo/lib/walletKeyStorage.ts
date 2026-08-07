import { generateRandomPrivateKey } from "./randomKey"

export const WALLET_KEY_STORAGE_KEY = "octobot-client-demo:wallet-key"

/** Storage is narrowed to just the methods used, so a test can pass a plain
 *  object instead of a real `Storage` / mocked `localStorage`. */
type Reader = Pick<Storage, "getItem">
type Writer = Pick<Storage, "setItem">

/** Reads a previously persisted key, or `null` if there isn't one (never
 *  written yet, or storage is unavailable/throws — private browsing, quota,
 *  disabled storage, …). Never throws. */
export function loadStoredPrivateKey(storage: Reader): string | null {
  try {
    return storage.getItem(WALLET_KEY_STORAGE_KEY) || null
  } catch {
    return null
  }
}

/** Best-effort persist — swallows a storage failure rather than crashing the
 *  demo over an unavailable localStorage. */
export function persistPrivateKey(storage: Writer, key: string): void {
  try {
    storage.setItem(WALLET_KEY_STORAGE_KEY, key)
  } catch {
    // Private browsing / storage disabled — the demo still works, it just
    // won't remember the key across a reload.
  }
}

/** The wallet key's actual startup contract: reuse whatever was persisted
 *  last time, generate fresh only if nothing was. This is the exact
 *  regression this module exists to prevent — the demo used to always
 *  generate a brand-new key on every page load
 *  (`useState(() => generateRandomPrivateKey())`, no read), which silently
 *  swapped wallets out from under anyone who had authorized their key on a
 *  real node and then reloaded the page. */
export function resolveInitialPrivateKey(storage: Reader): string {
  return loadStoredPrivateKey(storage) ?? generateRandomPrivateKey()
}

/** Referencing the `localStorage` global itself — not just calling a method
 *  on it — can throw in some sandboxed/policy-restricted contexts. Callers
 *  must go through this rather than passing `localStorage` directly, or that
 *  throw happens outside `loadStoredPrivateKey`/`persistPrivateKey`'s own
 *  try/catch. */
export function safeLocalStorage(): Storage | null {
  try {
    return localStorage
  } catch {
    return null
  }
}
