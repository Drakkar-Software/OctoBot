export function truncateAddress(address: string): string {
  if (address.length <= 12) return address
  return `${address.slice(0, 6)}…${address.slice(-4)}`
}

/** Reference label for debug wallet selector width — e.g. named wallet + truncated address. */
export const DEBUG_WALLET_SELECTOR_REFERENCE_LABEL = "groot (0x99d3…55c1)"

export const DEBUG_WALLET_SELECTOR_LAYOUT_CLASS =
  "h-8 max-w-xs shrink-0 rounded-md border border-rule px-3 text-sm"

export function getDebugWalletSelectorWidthStyle(): { width: string } {
  return {
    width: `calc(${DEBUG_WALLET_SELECTOR_REFERENCE_LABEL.length}ch + 1.5rem)`,
  }
}

export function formatWalletSelectOptionLabel(wallet: {
  name?: string | null
  address: string
}): string {
  const truncatedAddress = truncateAddress(wallet.address)
  const name = wallet.name?.trim()
  if (name) return `${name} (${truncatedAddress})`
  return `${truncatedAddress} (${truncatedAddress})`
}
