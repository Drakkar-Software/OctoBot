import { describe, expect, it } from "vitest"

import { isWalletBackupPromptEligible } from "@/lib/wallet-backup-prompt"

describe("isWalletBackupPromptEligible", () => {
  it("is true when wallet is configured and not acknowledged", () => {
    expect(
      isWalletBackupPromptEligible({
        walletConfigured: true,
        backupSavedAck: false,
      }),
    ).toBe(true)
  })

  it("is false when backup saved ack is set", () => {
    expect(
      isWalletBackupPromptEligible({
        walletConfigured: true,
        backupSavedAck: true,
      }),
    ).toBe(false)
  })

  it("is false when wallet is not configured", () => {
    expect(
      isWalletBackupPromptEligible({
        walletConfigured: false,
        backupSavedAck: false,
      }),
    ).toBe(false)
  })
})
