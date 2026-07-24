import { Link } from "@tanstack/react-router"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { OCTOBOT_WEB_INTERFACE_URL } from "@/lib/external-links"

const NODE_PROCESS_NOTE =
  "This node runs the strategy (you will need the node process to run)."

const AUTOMATION_RESUME_NOTE =
  "Started automations will show up in this node's dashboard and will automatically resume if you stop and restart your OctoBot node."

type StartAutomationDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  onAcknowledge?: () => void
}

export function StartAutomationDialog({
  open,
  onOpenChange,
  onAcknowledge,
}: StartAutomationDialogProps) {
  const handleAcknowledge = () => {
    onOpenChange(false)
    onAcknowledge?.()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Start your automation from the interface</DialogTitle>
          <DialogDescription asChild>
            <div className="flex flex-col gap-3 pt-1 text-sm text-muted-foreground">
              <p>
                Create a new automation in the OctoBot web or  mobile app.
              </p>
            </div>
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4 border-t pt-4">
          <p className="text-center text-sm text-muted-foreground">
            Use the OctoBot interface to create your automation:
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col items-center gap-2 rounded-md border p-4">
              <span className="text-sm font-medium">Browser</span>
              <p className="text-center text-sm text-muted-foreground">
                Open the{" "}
                <a
                  href={OCTOBOT_WEB_INTERFACE_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline underline-offset-4 hover:text-foreground"
                >
                  OctoBot web interface
                </a>{" "}
                and create a new automation.
              </p>
            </div>
            <div className="flex flex-col items-center gap-2 rounded-md border p-4">
              <span className="text-sm font-medium">Mobile app</span>
              <p className="text-center text-sm text-muted-foreground">
                Open your OctoBot app and create a new automation.
              </p>
            </div>
          </div>
          <p className="text-center text-sm text-muted-foreground">
            Need help connecting your interface? See the{" "}
            <Link
              to="/settings/connect"
              className="underline underline-offset-4 hover:text-foreground"
            >
              step-by-step guide
            </Link>
            .
          </p>
          <p className="border-t pt-4 text-center text-sm text-muted-foreground">
            {NODE_PROCESS_NOTE}
          </p>
          <div className="rounded-md border bg-muted/50 p-3 text-sm text-muted-foreground">
            <p>{AUTOMATION_RESUME_NOTE}</p>
          </div>
          <div className="flex flex-wrap justify-center gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
            >
              Close
            </Button>
            {onAcknowledge && (
              <Button type="button" variant="outline" onClick={handleAcknowledge}>
                ✓ I will use the web or mobile app
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
