import { buildAuthHeader } from "@/lib/node-config"

export type WalletExportData = {
  private_key: string
  seed?: string | null
}

export async function fetchOwnWalletExport(): Promise<WalletExportData> {
  const response = await fetch("/api/v1/setup/wallet/export", {
    headers: { Authorization: await buildAuthHeader() },
  })
  if (!response.ok) {
    throw new Error(await response.text())
  }
  return response.json()
}

export async function fetchWalletExport(
  walletAddress: string,
  passphrase: string,
): Promise<WalletExportData> {
  const params = new URLSearchParams({
    address: walletAddress,
    passphrase,
  })
  const response = await fetch(`/api/v1/setup/wallet/export?${params}`, {
    headers: { Authorization: await buildAuthHeader() },
  })
  if (!response.ok) {
    throw new Error(await response.text())
  }
  return response.json()
}
