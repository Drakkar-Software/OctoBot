import { CollapsibleJsonView } from "@/components/ui/collapsible-json-view"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

type JsonDetailDialogProps = {
  title: string
  data: unknown
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function JsonDetailDialog({
  title,
  data,
  open,
  onOpenChange,
}: JsonDetailDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>Full JSON payload</DialogDescription>
        </DialogHeader>
        {data != null ? (
          <CollapsibleJsonView value={data} />
        ) : (
          <p className="text-sm text-muted-foreground">—</p>
        )}
      </DialogContent>
    </Dialog>
  )
}
