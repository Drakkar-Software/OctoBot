import { createContext, type ReactNode, useContext, useState } from "react"
import { generateRandomPrivateKey } from "./randomKey"
import {
  persistPrivateKey,
  resolveInitialPrivateKey,
  safeLocalStorage,
} from "./walletKeyStorage"

type WalletKeyContextValue = {
  privateKey: string
  setPrivateKey: (key: string) => void
  regenerate: () => void
}

// One private key, shared by every section that represents "your wallet"
// (derive, queue/connect, propose) — so loading your own key in one place is
// reflected everywhere else that touches a real node, instead of each
// section silently holding its own.
//
// Persisted to localStorage, same as the node URL right next to it. This
// used to regenerate on every page load, which silently swapped wallets
// underneath anyone who had authorized a key on their node — the very next
// call after a reload would 403 with no indication the identity had
// changed. This is a throwaway demo key, not a real wallet, so keeping it in
// localStorage is an acceptable trust model here — `regenerate()` is the
// explicit escape hatch for anyone who wants a fresh identity instead.
//
// The load/persist logic lives in `walletKeyStorage.ts`, tested there — kept
// out of this file so the regression it guards against (see
// `resolveInitialPrivateKey`'s doc comment) has a unit test that doesn't
// need a React renderer.
//
// The website-pairing simulation's "phone" wallet is deliberately NOT this
// context — that's a second, independent device by design.
const WalletKeyContext = createContext<WalletKeyContextValue | null>(null)

export function WalletKeyProvider({ children }: { children: ReactNode }) {
  const [privateKey, setPrivateKeyState] = useState(() => {
    const storage = safeLocalStorage()
    return storage
      ? resolveInitialPrivateKey(storage)
      : generateRandomPrivateKey()
  })
  const setPrivateKey = (key: string) => {
    setPrivateKeyState(key)
    const storage = safeLocalStorage()
    if (storage) persistPrivateKey(storage, key)
  }
  const regenerate = () => setPrivateKey(generateRandomPrivateKey())
  return (
    <WalletKeyContext.Provider
      value={{ privateKey, setPrivateKey, regenerate }}
    >
      {children}
    </WalletKeyContext.Provider>
  )
}

export function useWalletKey(): WalletKeyContextValue {
  const ctx = useContext(WalletKeyContext)
  if (!ctx)
    throw new Error("useWalletKey must be used within a WalletKeyProvider")
  return ctx
}
