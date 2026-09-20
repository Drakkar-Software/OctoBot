export const WALLET_BACKUP_PROMPT_DELAY_MS = 48 * 60 * 60 * 1000

export function isWalletBackupPromptEligible({
  setupSucceededAtMs,
  nowMs,
  backupSavedAck,
}: {
  setupSucceededAtMs: number | null
  nowMs: number
  backupSavedAck: boolean
}): boolean {
  if (backupSavedAck) {
    return false
  }
  if (setupSucceededAtMs == null) {
    return false
  }
  return nowMs - setupSucceededAtMs >= WALLET_BACKUP_PROMPT_DELAY_MS
}
