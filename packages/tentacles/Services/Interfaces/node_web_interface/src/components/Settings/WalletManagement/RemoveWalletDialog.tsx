import { useMutation } from "@tanstack/react-query"
import { Trash2, TriangleAlert } from "lucide-react"
import { useState } from "react"
import { type WalletInfo, WalletsService } from "@/client"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { truncateAddress } from "@/lib/wallet-utils"

export function RemoveWalletDialog({
  wallet,
  onSuccess,
}: {
  wallet: WalletInfo
  onSuccess: () => void
}) {
  const [open, setOpen] = useState(false)

  const mutation = useMutation({
    mutationFn: () => WalletsService.deleteWallet({ address: wallet.address }),
    onSuccess: () => {
      setOpen(false)
      onSuccess()
    },
  })

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        mutation.reset()
        setOpen(v)
      }}
    >
      <DialogTrigger asChild>
        <button
          type="button"
          className="text-muted-foreground hover:text-destructive transition-colors"
          title="Remove wallet"
          aria-label="Remove wallet"
        >
          <Trash2 className="size-4" />
        </button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Remove wallet</DialogTitle>
          <DialogDescription>
            This will permanently remove{" "}
            <span className="font-mono">
              {wallet.name || truncateAddress(wallet.address)}
            </span>{" "}
            from this node.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex items-start gap-2 rounded-md border border-warn/30 bg-warn/10 p-3 text-sm text-warn">
            <TriangleAlert className="mt-0.5 size-4 shrink-0" />
            <span>
              Tasks associated with this wallet will become orphaned (visible to
              admins only). This action cannot be undone.
            </span>
          </div>
          {mutation.isError && (
            <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
              <TriangleAlert className="mt-0.5 size-4 shrink-0" />
              <span>
                {mutation.error instanceof Error
                  ? mutation.error.message
                  : "Failed to remove wallet"}
              </span>
            </div>
          )}
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-accent"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={mutation.isPending}
              onClick={() => mutation.mutate()}
              className="inline-flex items-center gap-2 rounded-md bg-destructive px-3 py-1.5 text-sm font-medium text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50"
            >
              {mutation.isPending ? "Removing…" : "Remove"}
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
