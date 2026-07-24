import { TriangleAlert } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  OCTOBOT_PLAY_STORE_URL,
  OCTOBOT_TESTFLIGHT_URL,
  OCTOBOT_WEB_INTERFACE_URL,
} from "@/lib/external-links"
import type { WalletSecretType } from "@/lib/use-confirm-wallet-secret-copy"

type ConfirmWalletSecretCopyDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  secretType: WalletSecretType
  onConfirm: () => void
}

const DIALOG_COPY: Record<
  WalletSecretType,
  { title: string; confirmLabel: string }
> = {
  private_key: {
    title: "Confirm private key copy",
    confirmLabel: "I confirm I want to copy my key",
  },
  seed_phrase: {
    title: "Confirm seed phrase copy",
    confirmLabel: "I confirm I want to copy my seed phrase",
  },
}

export function ConfirmWalletSecretCopyDialog({
  open,
  onOpenChange,
  secretType,
  onConfirm,
}: ConfirmWalletSecretCopyDialogProps) {
  const { title, confirmLabel } = DIALOG_COPY[secretType]

  const handleConfirm = () => {
    onConfirm()
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription asChild>
            <div className="flex flex-col gap-3 pt-1 text-sm text-muted-foreground">
              <p>
                Only paste this secret into the official OctoBot web interface or
                mobile app.
              </p>
              <p>
                Pasting it anywhere else is extremely dangerous. In 99% of
                cases, it is a scam attempt to steal your account.
              </p>
              <p>
                Never share your private key or seed phrase with anyone. Even the
                OctoBot support team will never ask you for your keys.
              </p>
            </div>
          </DialogDescription>
        </DialogHeader>
        <div className="flex items-start gap-2 rounded-md border border-warn/30 bg-warn/10 p-3 text-sm text-warn">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" />
          <span>
            Do not paste your secret into websites, chats, forms, or tools other
            than the official OctoBot interfaces listed below.
          </span>
        </div>
        <div className="flex flex-col gap-3 text-sm">
          <div className="flex flex-col gap-1">
            <span className="font-medium">Official OctoBot web interface</span>
            <a
              href={OCTOBOT_WEB_INTERFACE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-md border bg-muted px-3 py-2 text-xs break-all hover:text-foreground"
            >
              <code>{OCTOBOT_WEB_INTERFACE_URL}</code>
            </a>
          </div>
          <p>
            <a
              href={OCTOBOT_PLAY_STORE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-4 hover:text-foreground"
            >
              OctoBot on Google Play
            </a>
          </p>
          <p>
            <a
              href={OCTOBOT_TESTFLIGHT_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-4 hover:text-foreground"
            >
              OctoBot on TestFlight (iOS beta)
            </a>
          </p>
        </div>
        <DialogFooter className="mt-2">
          <DialogClose asChild>
            <Button type="button" variant="outline">
              Cancel
            </Button>
          </DialogClose>
          <Button type="button" onClick={handleConfirm}>
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
