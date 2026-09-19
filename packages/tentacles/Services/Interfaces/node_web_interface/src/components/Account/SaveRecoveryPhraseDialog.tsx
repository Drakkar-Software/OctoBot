import { Copy, TriangleAlert } from "lucide-react"
import { useState } from "react"

import { ConfirmWalletSecretCopyDialog } from "@/components/Common/ConfirmWalletSecretCopyDialog"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  acknowledgeRecoveryPhraseSaved,
  formatRecoveryPhraseWords,
} from "@/lib/recovery-phrase"
import { useConfirmWalletSecretCopy } from "@/lib/use-confirm-wallet-secret-copy"

type SaveRecoveryPhraseDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  seed: string
  onSaved: () => void
}

export function SaveRecoveryPhraseDialog({
  open,
  onOpenChange,
  seed,
  onSaved,
}: SaveRecoveryPhraseDialogProps) {
  const words = formatRecoveryPhraseWords(seed)
  const [saving, setSaving] = useState(false)
  const walletSecretCopy = useConfirmWalletSecretCopy()

  const handleConfirmSaved = async () => {
    setSaving(true)
    try {
      await acknowledgeRecoveryPhraseSaved()
      onSaved()
      onOpenChange(false)
    } finally {
      setSaving(false)
    }
  }

  const copyPhrase = () => {
    walletSecretCopy.requestCopy(seed, "seed_phrase")
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Your recovery phrase</DialogTitle>
            <DialogDescription>
              Write these words down and keep them offline. You need them if you
              forget your passphrase.
            </DialogDescription>
          </DialogHeader>
          <div className="flex items-start gap-2 rounded-md border border-warn/30 bg-warn/10 p-3 text-sm text-warn">
            <TriangleAlert className="mt-0.5 size-4 shrink-0" />
            <span>
              Anyone with these words can restore your account. Never share them.
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {words.map((word, index) => (
              <div
                key={`${index}-${word}`}
                className="rounded-md border bg-muted px-3 py-2 text-sm font-mono"
              >
                <span className="text-muted-foreground mr-2">{index + 1}.</span>
                {word}
              </div>
            ))}
          </div>
          <Button type="button" variant="outline" onClick={copyPhrase}>
            <Copy className="size-4" />
            Copy phrase
          </Button>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Not now
            </Button>
            <LoadingButton type="button" loading={saving} onClick={() => void handleConfirmSaved()}>
              I&apos;ve saved it
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <ConfirmWalletSecretCopyDialog
        open={walletSecretCopy.confirmOpen}
        onOpenChange={walletSecretCopy.handleOpenChange}
        secretType={walletSecretCopy.pendingSecretType}
        onConfirm={walletSecretCopy.handleConfirm}
      />
    </>
  )
}
