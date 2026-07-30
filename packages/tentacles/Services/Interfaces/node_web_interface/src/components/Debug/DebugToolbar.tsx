import { Download, Play, RefreshCw, Upload } from "lucide-react"

import type { WalletInfo } from "@/client"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  DEBUG_WALLET_SELECTOR_LAYOUT_CLASS,
  formatWalletSelectOptionLabel,
  getDebugWalletSelectorWidthStyle,
} from "@/lib/wallet-utils"
import { cn } from "@/lib/utils"

type DebugToolbarProps = {
  isImportedMode: boolean
  isSuperuser: boolean
  isWalletsLoading?: boolean
  wallets: WalletInfo[]
  walletAddress: string
  onWalletAddressChange: (address: string) => void
  onImport: () => void
  onReturnToLive: () => void
  onExport: () => void
  canExportSnapshot: boolean
  isRefreshPending?: boolean
  onRefresh: () => void
  onExecute: () => void
}

export function DebugToolbar({
  isImportedMode,
  isSuperuser,
  isWalletsLoading = false,
  wallets,
  walletAddress,
  onWalletAddressChange,
  onImport,
  onReturnToLive,
  onExport,
  canExportSnapshot,
  isRefreshPending = false,
  onRefresh,
  onExecute,
}: DebugToolbarProps) {
  if (isImportedMode) {
    return (
      <>
        <Button variant="outline" size="sm" onClick={onImport}>
          <Upload className="size-4" />
          Import
        </Button>
        <Button variant="outline" size="sm" onClick={onReturnToLive}>
          Return to live view
        </Button>
      </>
    )
  }

  const walletSelectorWidthStyle = getDebugWalletSelectorWidthStyle()

  return (
    <>
      {isSuperuser &&
        (isWalletsLoading ? (
          <Skeleton
            style={walletSelectorWidthStyle}
            className={DEBUG_WALLET_SELECTOR_LAYOUT_CLASS}
            aria-label="Loading wallets"
          />
        ) : (
          <select
            id="debug-wallet"
            aria-label="Wallet"
            style={walletSelectorWidthStyle}
            className={cn(
              DEBUG_WALLET_SELECTOR_LAYOUT_CLASS,
              "bg-input text-foreground focus:outline-none focus:ring-1 focus:ring-frost",
            )}
            value={walletAddress}
            onChange={(event) => onWalletAddressChange(event.target.value)}
          >
            {wallets.map((wallet) => (
              <option key={wallet.address} value={wallet.address}>
                {formatWalletSelectOptionLabel(wallet)}
              </option>
            ))}
          </select>
        ))}
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
      <Button
        variant="outline"
        size="sm"
        onClick={onRefresh}
        disabled={isRefreshPending}
      >
        <RefreshCw
          className={cn("size-4", isRefreshPending && "animate-spin")}
        />
        Refresh
      </Button>
      <Button size="sm" onClick={onExecute}>
        <Play className="size-4" />
        Execute
      </Button>
    </>
  )
}
