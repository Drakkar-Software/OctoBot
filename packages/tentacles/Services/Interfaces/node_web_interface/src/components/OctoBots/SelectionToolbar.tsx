import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Link, useNavigate } from "@tanstack/react-router"
import { Ban, ScrollText, Trash2 } from "lucide-react"
import { useMemo, useState } from "react"

import type { Task_Output as Task } from "@/client"
import { TasksService } from "@/client"
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
import { shareWorkflowLogs } from "@/lib/support-share"
import { getTaskFilterGroup } from "@/utils/task-status"

/** Copy for the "Share logs" guidance modal, keyed by the resolved ticket state. */
const LOGS_MODAL_COPY = {
  none: {
    title: "No support ticket",
    body: "Please create a support ticket before sharing logs.",
  },
  pending: {
    title: "Ticket not yet accepted",
    body: "The DRAKKAR-SOFTWARE team has not yet accepted your ticket. Please wait until they accept it before sharing any logs, and retry later.",
  },
  disabled: {
    title: "Support unavailable",
    body: "Support chat isn't available on this OctoBot.",
  },
} as const

export function SelectionToolbar({
  selectedIds,
  filteredTasks,
  allTasks,
  onSelectAll,
  onDeselectAll,
  onDeleted,
}: {
  selectedIds: Set<string>
  filteredTasks: Task[]
  allTasks: Task[]
  onSelectAll: () => void
  onDeselectAll: () => void
  onDeleted: () => void
}) {
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [exportLoading, setExportLoading] = useState(false)
  const [logsModal, setLogsModal] = useState<
    null | "none" | "pending" | "disabled"
  >(null)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const activeTasks = useMemo(
    () =>
      allTasks.filter(
        (t) =>
          t.id && selectedIds.has(t.id) && getTaskFilterGroup(t) === "active",
      ),
    [allTasks, selectedIds],
  )

  const inactiveTasks = useMemo(
    () =>
      allTasks.filter(
        (t) =>
          t.id && selectedIds.has(t.id) && getTaskFilterGroup(t) !== "active",
      ),
    [allTasks, selectedIds],
  )

  const deleteMutation = useMutation({
    mutationFn: () =>
      TasksService.deleteTasks({
        taskIds: inactiveTasks.map((t) => t.id as string),
      }),
    onSuccess: () => {
      showSuccessToast(
        `Deleted ${inactiveTasks.length} OctoBot${inactiveTasks.length !== 1 ? "s" : ""}`,
      )
      setDeleteOpen(false)
      onDeleted()
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
    },
    onError: () => {
      showErrorToast("Some deletions failed")
    },
  })

  const cancelMutation = useMutation({
    mutationFn: () =>
      TasksService.cancelTasks({
        requestBody: { task_ids: activeTasks.map((t) => t.id as string) },
      }),
    onSuccess: () => {
      showSuccessToast(
        `Cancelled ${activeTasks.length} OctoBot${activeTasks.length !== 1 ? "s" : ""}`,
      )
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
    },
    onError: () => {
      showErrorToast("Some cancellations failed")
    },
  })

  const shareLogsMutation = useMutation({
    mutationFn: () => shareWorkflowLogs(Array.from(selectedIds)),
    onSuccess: (res) => {
      if (res.status === "shared") {
        showSuccessToast("Workflow logs shared to your support ticket")
      } else {
        setLogsModal(res.status)
      }
    },
    onError: (err) =>
      showErrorToast(
        err instanceof Error ? err.message : "Couldn't share logs",
      ),
  })

  const exportableTasks = inactiveTasks

  const handleExportResults = () => {
    if (exportableTasks.length === 0) {
      showErrorToast("No results to export for selected OctoBots")
      return
    }
    setExportLoading(true)
    const taskIds = exportableTasks
      .map((t) => t.id)
      .filter(Boolean)
      .join(",")
    navigate({ to: "/octobots/export", search: { tasks: taskIds } })
  }

  const allFilteredSelected = filteredTasks.every(
    (t) => t.id && selectedIds.has(t.id),
  )

  return (
    <>
      <div className="flex flex-wrap items-center gap-2 rounded-card border border-rule bg-surface-soft px-4 py-2 text-sm">
        <span className="font-medium">{selectedIds.size} selected</span>
        <div className="flex gap-2">
          {!allFilteredSelected && (
            <Button variant="ghost" size="sm" onClick={onSelectAll}>
              Select all
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={onDeselectAll}>
            Deselect all
          </Button>
        </div>
        <div className="ml-auto flex flex-wrap gap-2">
          <LoadingButton
            variant="outline"
            size="sm"
            loading={exportLoading}
            onClick={handleExportResults}
          >
            Export results
          </LoadingButton>
          <LoadingButton
            variant="outline"
            size="sm"
            loading={shareLogsMutation.isPending}
            onClick={() => shareLogsMutation.mutate()}
          >
            <ScrollText className="size-3.5" />
            Share logs
          </LoadingButton>
          {activeTasks.length > 0 && (
            <LoadingButton
              variant="outline"
              size="sm"
              loading={cancelMutation.isPending}
              onClick={() => cancelMutation.mutate()}
            >
              <Ban className="size-3.5" />
              Cancel
            </LoadingButton>
          )}
          {inactiveTasks.length > 0 && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setDeleteOpen(true)}
            >
              <Trash2 className="size-3.5" />
              Delete
            </Button>
          )}
        </div>
      </div>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              Delete {inactiveTasks.length} OctoBot
              {inactiveTasks.length !== 1 ? "s" : ""}
            </DialogTitle>
            <DialogDescription>
              This will permanently delete the selected OctoBots. This action
              cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4">
            <DialogClose asChild>
              <Button variant="outline" disabled={deleteMutation.isPending}>
                Cancel
              </Button>
            </DialogClose>
            <LoadingButton
              variant="destructive"
              loading={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
            >
              Delete
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={logsModal !== null}
        onOpenChange={(open) => !open && setLogsModal(null)}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {logsModal !== null && LOGS_MODAL_COPY[logsModal].title}
            </DialogTitle>
            <DialogDescription>
              {logsModal !== null && LOGS_MODAL_COPY[logsModal].body}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4">
            <DialogClose asChild>
              <Button variant="outline">Close</Button>
            </DialogClose>
            {logsModal === "none" && (
              <Button asChild>
                <Link to="/settings">Go to Settings</Link>
              </Button>
            )}
            {logsModal === "pending" && (
              <Button variant="outline" asChild>
                <Link to="/support">View status</Link>
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
