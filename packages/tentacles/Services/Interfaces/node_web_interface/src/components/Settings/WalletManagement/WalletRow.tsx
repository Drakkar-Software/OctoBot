import { useMutation } from "@tanstack/react-query"
import { Copy, ShieldCheck } from "lucide-react"
import { useEffect, useState } from "react"
import { type WalletInfo, WalletsService } from "@/client"
import { ExportWalletDialog } from "@/components/Settings/WalletManagement/ExportWalletDialog"
import { PairDeviceDialog } from "@/components/Settings/WalletManagement/PairDeviceDialog"
import { RemoveWalletDialog } from "@/components/Settings/WalletManagement/RemoveWalletDialog"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { copyTextToClipboard } from "@/lib/clipboard"
import { truncateAddress } from "@/lib/wallet-utils"

export function WalletRow({
  wallet,
  onRefresh,
  showRemove = true,
  showExport = false,
  currentUserAddress = "",
}: {
  wallet: WalletInfo
  onRefresh: () => void
  showRemove?: boolean
  showExport?: boolean
  currentUserAddress?: string
}) {
  const [editing, setEditing] = useState(false)
  const [nameValue, setNameValue] = useState(wallet.name ?? "")
  const [renameError, setRenameError] = useState<string | null>(null)

  useEffect(() => {
    if (!editing) setNameValue(wallet.name ?? "")
  }, [wallet.name, editing])

  const mutation = useMutation({
    mutationFn: (name: string | null) =>
      WalletsService.updateWallet({
        address: wallet.address,
        requestBody: { name },
      }),
    onSuccess: () => {
      setEditing(false)
      setRenameError(null)
      onRefresh()
    },
    onError: (e: unknown) => {
      setRenameError(e instanceof Error ? e.message : "Failed to rename wallet")
    },
  })

  const handleSave = () => {
    mutation.mutate(nameValue.trim() || null)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSave()
    if (e.key === "Escape") {
      setEditing(false)
      setNameValue(wallet.name ?? "")
    }
  }

  const isOwnWallet =
    wallet.address.toLowerCase() === currentUserAddress.toLowerCase()
  const loginUsernameCopyLabel = `Copy login username ${wallet.address}`

  return (
    <div className="flex items-center gap-3 rounded-lg border p-3">
      <div className="flex-1 min-w-0 flex flex-col gap-0.5">
        {editing ? (
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <input
                className="rounded border border-rule bg-input px-2 py-0.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-frost"
                value={nameValue}
                onChange={(e) => setNameValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Display name"
              />
              <button
                type="button"
                onClick={handleSave}
                disabled={mutation.isPending}
                className="text-xs text-primary hover:underline disabled:opacity-50"
              >
                {mutation.isPending ? "Saving…" : "Save"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setEditing(false)
                  setNameValue(wallet.name ?? "")
                  setRenameError(null)
                  mutation.reset()
                }}
                className="text-xs text-muted-foreground hover:underline"
              >
                Cancel
              </button>
            </div>
            {renameError && (
              <span className="text-xs text-destructive">{renameError}</span>
            )}
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="flex min-w-0 max-w-full items-center gap-1.5 text-left group"
            title="Click to edit name"
          >
            <span className="truncate text-sm font-medium group-hover:underline underline-offset-2">
              {wallet.name || (
                <span className="text-muted-foreground italic">No name</span>
              )}
            </span>
          </button>
        )}
        {isOwnWallet ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                className="text-xs text-muted-foreground font-mono text-left cursor-pointer hover:text-foreground w-fit"
                aria-label={loginUsernameCopyLabel}
                onClick={() =>
                  copyTextToClipboard(
                    wallet.address,
                    "Node login username (admin address)",
                  )
                }
              >
                <span className="inline-flex items-center gap-1">
                  {truncateAddress(wallet.address)}
                  <Copy className="size-3.5 shrink-0 opacity-70" aria-hidden />
                </span>
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-md p-3">
              <div className="flex flex-col gap-1">
                <span className="font-mono text-xs break-all">
                  {wallet.address}
                </span>
                <span className="text-xs font-sans">
                  Username for browser-app login
                </span>
              </div>
            </TooltipContent>
          </Tooltip>
        ) : (
          <span className="text-xs text-muted-foreground font-mono">
            {truncateAddress(wallet.address)}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {showExport && (
          <ExportWalletDialog
            walletAddress={wallet.address}
            isOwnWallet={isOwnWallet}
          />
        )}
        {isOwnWallet ? <PairDeviceDialog /> : null}
        {wallet.is_admin && (
          <Tooltip>
            <TooltipTrigger asChild>
              <span>
                <ShieldCheck className="size-4 text-primary" />
              </span>
            </TooltipTrigger>
            <TooltipContent side="left">Admin wallet</TooltipContent>
          </Tooltip>
        )}
        {wallet.is_admin === false && showRemove && (
          <RemoveWalletDialog wallet={wallet} onSuccess={onRefresh} />
        )}
      </div>
    </div>
  )
}
