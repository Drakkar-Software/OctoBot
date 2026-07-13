import { useMutation, useQueryClient } from "@tanstack/react-query"
import { TriangleAlert } from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import type { Task_Output as Task } from "@/client"
import { DebugService } from "@/client"
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
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import {
  buildStopAutomationUserAction,
  formatStopAutomationError,
  getOctoBotDisplayName,
} from "@/lib/octobots/stop-automation"

type StopAutomationDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  tasks: Task[]
  onSuccess?: () => void
}

function buildStopDescription(tasks: Task[]): string {
  if (tasks.length === 1) {
    const displayName = getOctoBotDisplayName(tasks[0])
    return `Stop ${displayName}? This will stop the automation and end its current run.`
  }
  const previewNames = tasks
    .slice(0, 3)
    .map((task) => getOctoBotDisplayName(task))
    .join(", ")
  const suffix =
    tasks.length > 3 ? ` and ${tasks.length - 3} more` : ""
  return `Stop ${tasks.length} OctoBots (${previewNames}${suffix})? This will stop each automation and end its current run.`
}

async function stopAutomationsSequentially(
  automationIds: string[],
): Promise<{ failed: { automationId: string; message: string }[] }> {
  const failed: { automationId: string; message: string }[] = []
  for (const automationId of automationIds) {
    try {
      await DebugService.executeUserAction({
        requestBody: buildStopAutomationUserAction(automationId),
        walletAddress: null,
      })
    } catch (error) {
      failed.push({
        automationId,
        message: formatStopAutomationError(error),
      })
    }
  }
  return { failed }
}

function formatBulkStopError(
  totalCount: number,
  failed: { automationId: string; message: string }[],
): string {
  if (failed.length === 0) return ""
  const header = `${failed.length} of ${totalCount} stop request${totalCount !== 1 ? "s" : ""} failed.`
  const details = failed
    .map((entry) => `${entry.automationId.slice(0, 8)}: ${entry.message}`)
    .join("\n")
  return `${header}\n${details}`
}

export function StopAutomationDialog({
  open,
  onOpenChange,
  tasks,
  onSuccess,
}: StopAutomationDialogProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const [submitError, setSubmitError] = useState<string | null>(null)

  const stoppableTasks = useMemo(
    () => tasks.filter((task): task is Task & { id: string } => Boolean(task.id)),
    [tasks],
  )

  useEffect(() => {
    if (open) {
      setSubmitError(null)
    }
  }, [open, stoppableTasks.map((task) => task.id).join(",")])

  const stopMutation = useMutation({
    mutationFn: (automationIds: string[]) =>
      stopAutomationsSequentially(automationIds),
    onSuccess: (result, automationIds) => {
      if (result.failed.length > 0) {
        setSubmitError(formatBulkStopError(automationIds.length, result.failed))
        queryClient.invalidateQueries({ queryKey: ["tasks"] })
        return
      }
      const count = automationIds.length
      showSuccessToast(
        count === 1
          ? "OctoBot stop requested"
          : `Stop requested for ${count} OctoBots`,
      )
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
      onOpenChange(false)
      onSuccess?.()
    },
    onError: (error) => {
      setSubmitError(formatStopAutomationError(error))
    },
  })

  const handleConfirm = () => {
    if (stoppableTasks.length === 0 || stopMutation.isPending) return
    setSubmitError(null)
    stopMutation.mutate(stoppableTasks.map((task) => task.id))
  }

  const title =
    stoppableTasks.length === 1 ? "Stop OctoBot" : `Stop ${stoppableTasks.length} OctoBots`

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            {buildStopDescription(stoppableTasks)}
          </DialogDescription>
        </DialogHeader>
        {submitError && (
          <div className="flex items-start gap-2 rounded-md border border-neg/25 border-l-2 border-l-neg/70 bg-neg/[0.07] px-2.5 py-1.5">
            <TriangleAlert className="mt-0.5 size-3.5 shrink-0 text-neg/80" />
            <p className="text-xs leading-snug text-neg/75 whitespace-pre-wrap break-words">
              {submitError}
            </p>
          </div>
        )}
        <DialogFooter className="mt-4">
          <DialogClose asChild>
            <Button variant="outline" disabled={stopMutation.isPending}>
              Cancel
            </Button>
          </DialogClose>
          <LoadingButton
            variant="destructive"
            loading={stopMutation.isPending}
            onClick={handleConfirm}
            disabled={stoppableTasks.length === 0}
          >
            Stop
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
