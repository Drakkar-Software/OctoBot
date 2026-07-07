import { useEffect, useMemo, useState } from "react"
import { toast } from "sonner"

import type { AutomationState } from "@/client"
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  AUTOMATION_TABLE_DEFAULT_SORT,
  ID_DISPLAY_LENGTH,
} from "@/lib/debug/constants"
import { getDebugStatusDisplay } from "@/lib/debug/display-utils"
import { sortAutomations } from "@/lib/debug/table-automations"
import {
  downloadAutomationLogsArchive,
  downloadNodeLogsArchive,
} from "@/lib/logs-export"

type LogsTarget = "node" | "automation"

type DownloadLogsDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  automations: AutomationState[]
}

function formatAutomationOptionLabel(automation: AutomationState): string {
  const truncatedId =
    automation.id.length > ID_DISPLAY_LENGTH
      ? `${automation.id.slice(0, ID_DISPLAY_LENGTH)}…`
      : automation.id
  const statusLabel = getDebugStatusDisplay(automation.status).label
  return `${automation.metadata.name} · ${statusLabel} (${truncatedId})`
}

export function DownloadLogsDialog({
  open,
  onOpenChange,
  automations,
}: DownloadLogsDialogProps) {
  const [target, setTarget] = useState<LogsTarget>("node")
  const [selectedAutomationId, setSelectedAutomationId] = useState("")
  const [downloading, setDownloading] = useState(false)

  const sortedAutomations = useMemo(
    () => sortAutomations(automations, AUTOMATION_TABLE_DEFAULT_SORT),
    [automations],
  )

  useEffect(() => {
    if (!open) return
    setTarget("node")
    setSelectedAutomationId(sortedAutomations[0]?.id ?? "")
    setDownloading(false)
  }, [open, sortedAutomations])

  const handleDownload = async () => {
    setDownloading(true)
    try {
      if (target === "node") {
        await downloadNodeLogsArchive()
      } else {
        const automation = sortedAutomations.find(
          (row) => row.id === selectedAutomationId,
        )
        if (!automation) {
          throw new Error("Select an automation")
        }
        await downloadAutomationLogsArchive(
          automation.id,
          automation.metadata.name,
        )
      }
      onOpenChange(false)
      toast.success("Logs archive downloaded")
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Couldn't download logs",
      )
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Download logs</DialogTitle>
          <DialogDescription>
            Download the node log files or logs for a single automation.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <fieldset className="flex flex-col gap-2">
            <legend className="sr-only">Log source</legend>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="logs-target"
                value="node"
                checked={target === "node"}
                onChange={() => setTarget("node")}
              />
              Node logs
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="logs-target"
                value="automation"
                checked={target === "automation"}
                onChange={() => setTarget("automation")}
              />
              Automation logs
            </label>
          </fieldset>

          {target === "automation" && (
            <div className="flex flex-col gap-1.5">
              <p className="text-xs font-medium text-muted-foreground">
                Automation
              </p>
              <Select
                value={selectedAutomationId}
                onValueChange={setSelectedAutomationId}
                disabled={sortedAutomations.length === 0}
              >
                <SelectTrigger size="sm" className="w-full max-w-none">
                  <SelectValue placeholder="No automations" />
                </SelectTrigger>
                <SelectContent>
                  {sortedAutomations.map((automation) => (
                    <SelectItem key={automation.id} value={automation.id}>
                      {formatAutomationOptionLabel(automation)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            type="button"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <LoadingButton
            loading={downloading}
            disabled={target === "automation" && sortedAutomations.length === 0}
            onClick={() => void handleDownload()}
          >
            Download
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
