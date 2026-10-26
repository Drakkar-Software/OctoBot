import { useEffect, useState } from "react"

import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import { Button } from "@/components/ui/button"
import { resolveDefaultHideLogTimings } from "@/lib/support-share"

export function ShareLogsDialog({
  open,
  onOpenChange,
  octobotCount,
  sharing,
  onShare,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  octobotCount: number
  sharing: boolean
  onShare: (hideLogTimings: boolean) => void
}) {
  const [hideLogTimings, setHideLogTimings] = useState(false)

  useEffect(() => {
    if (!open) {
      return
    }
    let cancelled = false
    void resolveDefaultHideLogTimings().then((defaultHide) => {
      if (!cancelled) {
        setHideLogTimings(defaultHide)
      }
    })
    return () => {
      cancelled = true
    }
  }, [open])

  const title =
    octobotCount === 1
      ? "Share logs to support"
      : `Share logs for ${octobotCount} OctoBots`

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            Attach the selected automation log files to your open support ticket.
          </DialogDescription>
        </DialogHeader>
        <div className="flex items-start gap-3 py-2">
          <Checkbox
            id="hide-log-timings"
            checked={hideLogTimings}
            disabled={sharing}
            onCheckedChange={(checked) => setHideLogTimings(checked === true)}
          />
          <div className="flex flex-col gap-1">
            <Label htmlFor="hide-log-timings" className="text-sm font-medium">
              Hide log timings
            </Label>
            <span className="text-xs text-muted-foreground">
              Replaces line timestamps with ordered numbers in the shared copy.
            </span>
          </div>
        </div>
        <DialogFooter className="mt-2">
          <DialogClose asChild>
            <Button variant="outline" disabled={sharing}>
              Cancel
            </Button>
          </DialogClose>
          <LoadingButton
            loading={sharing}
            onClick={() => onShare(hideLogTimings)}
          >
            Share
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
