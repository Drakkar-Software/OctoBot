import { QrCode, TriangleAlert } from "lucide-react"
import { useState } from "react"
import { QRCode } from "react-qr-code"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { loadPassword } from "@/lib/device-key"

export function PairDeviceDialog() {
  const [qrValue, setQrValue] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const buildQrValue = async () => {
    setError(null)
    try {
      const address = localStorage.getItem("auth_username") || ""
      const passphrase = (await loadPassword()) ?? ""
      if (!address || !passphrase) {
        throw new Error(
          "No active wallet session — log out and back in to refresh device key.",
        )
      }
      setQrValue(
        JSON.stringify({
          url: window.location.origin,
          address,
          passphrase,
        }),
      )
    } catch (e) {
      console.error("PairDeviceDialog: failed to build QR value", e)
      setError(e instanceof Error ? e.message : "Failed to build QR code")
    }
  }

  const onOpenChange = (open: boolean) => {
    if (open) {
      void buildQrValue()
    }
    if (!open) {
      setQrValue(null)
      setError(null)
    }
  }

  return (
    <Dialog onOpenChange={onOpenChange}>
      <Tooltip>
        <TooltipTrigger asChild>
          <DialogTrigger asChild>
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Pair device"
            >
              <QrCode className="size-4" />
            </button>
          </DialogTrigger>
        </TooltipTrigger>
        <TooltipContent side="left">Pair device</TooltipContent>
      </Tooltip>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Pair mobile device</DialogTitle>
          <DialogDescription>
            Scan this QR code with your OctoBot mobile app to connect to this
            node.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col items-center gap-4">
          <div className="flex items-start gap-2 rounded-md border border-warn/30 bg-warn/10 p-3 text-sm text-warn w-full">
            <TriangleAlert className="mt-0.5 size-4 shrink-0" />
            <span>
              Only scan on a trusted device. The QR code contains your
              passphrase.
            </span>
          </div>
          {error && (
            <p className="text-sm text-destructive text-center">{error}</p>
          )}
          {qrValue && (
            <div className="rounded-xl bg-white p-4">
              <QRCode value={qrValue} size={220} />
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
