import { Download, Play, RefreshCw, Upload } from "lucide-react"

import type { WalletInfo } from "@/client"
import { Button } from "@/components/ui/button"
import { truncateAddress } from "@/lib/wallet-utils"

type DebugToolbarProps = {
  isImportedMode: boolean
  isSuperuser: boolean
  wallets: WalletInfo[]
  walletAddress: string
  onWalletAddressChange: (address: string) => void
  onImport: () => void
  onReturnToLive: () => void
  onExport: () => void
  canExportSnapshot: boolean
  onRefresh: () => void
  onExecute: () => void
}

export function DebugToolbar({
  isImportedMode,
  isSuperuser,
  wallets,
  walletAddress,
  onWalletAddressChange,
  onImport,
  onReturnToLive,
  onExport,
  canExportSnapshot,
  onRefresh,
  onExecute,
}: DebugToolbarProps) {
  if (isImportedMode) {
    return (
      <div className="flex flex-wrap items-center justify-end gap-2">
        <Button variant="outline" size="sm" onClick={onImport}>
          <Upload className="size-4" />
          Import
        </Button>
        <Button variant="outline" size="sm" onClick={onReturnToLive}>
          Return to live view
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-wrap items-center justify-end gap-2">
      {isSuperuser && (
        <select
          id="debug-wallet"
          aria-label="Wallet"
          className="h-8 rounded-md border border-rule bg-input px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-frost max-w-xs"
          value={walletAddress}
          onChange={(event) => onWalletAddressChange(event.target.value)}
        >
          {wallets.map((wallet) => (
            <option key={wallet.address} value={wallet.address}>
              {wallet.name || truncateAddress(wallet.address)} (
              {truncateAddress(wallet.address)})
            </option>
          ))}
        </select>
      )}
      <Button variant="outline" size="sm" onClick={onImport}>
        <Upload className="size-4" />
        Import
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={onExport}
        disabled={!canExportSnapshot}
      >
        <Download className="size-4" />
        Export
      </Button>
      <Button variant="outline" size="sm" onClick={onRefresh}>
        <RefreshCw className="size-4" />
        Refresh
      </Button>
      <Button size="sm" onClick={onExecute}>
        <Play className="size-4" />
        Execute
      </Button>
    </div>
  )
}
