import {
  MobileUiPanel,
  type MobileUiPanelProps,
} from "@/components/Setup/MobileUiCard"
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
import { MOBILE_UI_DESCRIPTION, MOBILE_UI_TITLE } from "@/lib/mobile-ui"

type MobileUiDialogProps = MobileUiPanelProps & {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function MobileUiDialog({
  open,
  onOpenChange,
  readyLabel,
}: MobileUiDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{MOBILE_UI_TITLE}</DialogTitle>
          <DialogDescription>{MOBILE_UI_DESCRIPTION}</DialogDescription>
        </DialogHeader>
        <MobileUiPanel readyLabel={readyLabel} />
        <DialogFooter className="flex-row flex-wrap justify-end gap-2">
          <DialogClose asChild>
            <Button type="button" variant="secondary">
              Close
            </Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}