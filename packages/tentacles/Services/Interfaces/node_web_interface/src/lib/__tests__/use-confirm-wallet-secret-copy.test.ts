import { beforeEach, describe, expect, it, vi } from "vitest"

import {
  initialWalletSecretCopyState,
  performWalletSecretCopy,
  walletSecretCopyReducer,
} from "@/lib/use-confirm-wallet-secret-copy"

const toastSuccess = vi.fn()

vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
  },
}))

describe("walletSecretCopyReducer", () => {
  it("opens confirmation without copying when request_copy is dispatched", () => {
    const nextState = walletSecretCopyReducer(initialWalletSecretCopyState, {
      type: "request_copy",
      secret: "abc123",
      secretType: "private_key",
    })
    expect(nextState).toEqual({
      confirmOpen: true,
      pendingSecret: "abc123",
      pendingSecretType: "private_key",
    })
  })

  it("clears pending secret when open_change is false", () => {
    const openState = walletSecretCopyReducer(initialWalletSecretCopyState, {
      type: "request_copy",
      secret: "abc123",
      secretType: "seed_phrase",
    })
    const nextState = walletSecretCopyReducer(openState, {
      type: "open_change",
      open: false,
    })
    expect(nextState).toEqual(initialWalletSecretCopyState)
  })

  it("resets state after confirm", () => {
    const openState = walletSecretCopyReducer(initialWalletSecretCopyState, {
      type: "request_copy",
      secret: "abc123",
      secretType: "private_key",
    })
    const nextState = walletSecretCopyReducer(openState, { type: "confirm" })
    expect(nextState).toEqual(initialWalletSecretCopyState)
  })
})

describe("performWalletSecretCopy", () => {
  beforeEach(() => {
    toastSuccess.mockClear()
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    })
  })

  it("writes the private key to the clipboard and shows a toast", async () => {
    await performWalletSecretCopy("secret-value", "private_key")
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("secret-value")
    expect(toastSuccess).toHaveBeenCalledWith("Copied to clipboard", {
      description: "Private key",
    })
  })

  it("writes the seed phrase to the clipboard and shows a toast", async () => {
    await performWalletSecretCopy("seed words", "seed_phrase")
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("seed words")
    expect(toastSuccess).toHaveBeenCalledWith("Copied to clipboard", {
      description: "Seed phrase",
    })
  })
})
