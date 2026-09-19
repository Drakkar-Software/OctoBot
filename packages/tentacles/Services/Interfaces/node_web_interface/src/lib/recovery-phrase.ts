import { buildAuthHeader } from "@/lib/node-config"

export type RecoveryPhraseStatus = {
  has_recovery_phrase: boolean
  recovery_phrase_saved: boolean
}

export async function fetchRecoveryPhraseStatus(): Promise<RecoveryPhraseStatus> {
  const response = await fetch("/api/v1/wallets/me/recovery-phrase/status", {
    headers: { Authorization: await buildAuthHeader() },
  })
  if (!response.ok) {
    throw new Error(await response.text())
  }
  return response.json()
}

export async function fetchRecoveryPhrase(): Promise<string> {
  const response = await fetch("/api/v1/wallets/me/recovery-phrase", {
    headers: { Authorization: await buildAuthHeader() },
  })
  if (!response.ok) {
    throw new Error(await response.text())
  }
  const data: { seed: string } = await response.json()
  return data.seed
}

export async function acknowledgeRecoveryPhraseSaved(): Promise<void> {
  const response = await fetch("/api/v1/wallets/me/recovery-phrase/acknowledge", {
    method: "POST",
    headers: { Authorization: await buildAuthHeader() },
  })
  if (!response.ok) {
    throw new Error(await response.text())
  }
}

export type WalletRecoverResult = {
  address: string
}

export async function recoverWalletPassphrase(
  seed: string,
  newPassphrase: string,
): Promise<WalletRecoverResult> {
  const response = await fetch("/api/v1/setup/wallet/recover", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ seed: seed.trim(), new_passphrase: newPassphrase }),
  })
  if (!response.ok) {
    let detail = "Could not restore account"
    try {
      const payload = await response.json()
      if (typeof payload.detail === "string") {
        detail = payload.detail
      }
    } catch {
      // ignore parse errors
    }
    throw new Error(detail)
  }
  return response.json()
}

export function formatRecoveryPhraseWords(seed: string): string[] {
  return seed.trim().split(/\s+/).filter(Boolean)
}
