import { buildAuthHeader } from "@/lib/node-config"

export type WalletBackupPromptStatus = {
  wallet_setup_succeeded_at: number | null
  backup_saved_ack: boolean
}

export async function fetchWalletBackupPromptStatus(): Promise<WalletBackupPromptStatus> {
  const response = await fetch("/api/v1/setup/wallet/backup-prompt-status", {
    headers: { Authorization: await buildAuthHeader() },
  })
  if (!response.ok) {
    throw new Error("Failed to load wallet backup status")
  }
  return response.json()
}

export async function acknowledgeWalletBackupSaved(): Promise<void> {
  const response = await fetch("/api/v1/setup/wallet/backup-saved-ack", {
    method: "POST",
    headers: { Authorization: await buildAuthHeader() },
  })
  if (!response.ok) {
    throw new Error("Failed to save backup acknowledgement")
  }
}
