import { fetchOwnWalletExport, fetchWalletExport } from "@/lib/wallet-export"

/** Load the BIP39 phrase for a wallet just created with `passphrase` (generate path). */
export async function fetchSeedAfterWalletCreate(
  walletAddress: string,
  passphrase: string,
  options?: { isOwnWallet?: boolean },
): Promise<string | null> {
  const exportData =
    options?.isOwnWallet === false
      ? await fetchWalletExport(walletAddress, passphrase)
      : await fetchOwnWalletExport()
  const seed = exportData.seed?.trim()
  return seed || null
}
