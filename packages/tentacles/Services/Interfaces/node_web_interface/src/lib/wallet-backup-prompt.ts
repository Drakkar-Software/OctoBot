export function isWalletBackupPromptEligible({
  walletConfigured,
  backupSavedAck,
}: {
  walletConfigured: boolean
  backupSavedAck: boolean
}): boolean {
  if (backupSavedAck) {
    return false
  }
  return walletConfigured
}
