import { describe, expect, it } from "vitest"

import {
  isWalletBackupPromptEligible,
  WALLET_BACKUP_PROMPT_DELAY_MS,
} from "@/lib/wallet-backup-prompt"

describe("isWalletBackupPromptEligible", () => {
  const setupAt = 1_000_000

  it("is false before 48h elapsed", () => {
    expect(
      isWalletBackupPromptEligible({
        setupSucceededAtMs: setupAt,
        nowMs: setupAt + WALLET_BACKUP_PROMPT_DELAY_MS - 1,
        backupSavedAck: false,
      }),
    ).toBe(false)
  })

  it("is true after 48h when not acknowledged", () => {
    expect(
      isWalletBackupPromptEligible({
        setupSucceededAtMs: setupAt,
        nowMs: setupAt + WALLET_BACKUP_PROMPT_DELAY_MS,
        backupSavedAck: false,
      }),
    ).toBe(true)
  })

  it("is false when backup saved ack is set", () => {
    expect(
      isWalletBackupPromptEligible({
        setupSucceededAtMs: setupAt,
        nowMs: setupAt + WALLET_BACKUP_PROMPT_DELAY_MS + 10_000,
        backupSavedAck: true,
      }),
    ).toBe(false)
  })

  it("is false without setup timestamp", () => {
    expect(
      isWalletBackupPromptEligible({
        setupSucceededAtMs: null,
        nowMs: setupAt + WALLET_BACKUP_PROMPT_DELAY_MS,
        backupSavedAck: false,
      }),
    ).toBe(false)
  })
})
