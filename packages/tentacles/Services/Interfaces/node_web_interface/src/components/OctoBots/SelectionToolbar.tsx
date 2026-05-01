import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { Trash2 } from "lucide-react"
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
import { loadPassword } from "@/lib/device-key"
import { getTaskFilterGroup } from "@/utils/task-status"

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
  const [shareLogsOpen, setShareLogsOpen] = useState(false)
  const [shareLogsLoading, setShareLogsLoading] = useState(false)
  const [exportLoading, setExportLoading] = useState(false)
  const [shareCreds, setShareCreds] = useState<{
    errorId: string
    errorSecret: string
  } | null>(null)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const deleteMutation = useMutation({
    mutationFn: () =>
      TasksService.deleteTasks({ taskIds: Array.from(selectedIds) }),
    onSuccess: () => {
      showSuccessToast(
        `Deleted ${selectedIds.size} OctoBot${selectedIds.size !== 1 ? "s" : ""}`,
      )
      setDeleteOpen(false)
      onDeleted()
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
    },
    onError: () => {
      showErrorToast("Some deletions failed")
    },
  })

  const exportableTasks = useMemo(
    () =>
      allTasks.filter(
        (t) =>
          t.id && selectedIds.has(t.id) && getTaskFilterGroup(t) !== "active",
      ),
    [allTasks, selectedIds],
  )

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

  const handleShareLogs = async () => {
    setShareLogsLoading(true)
    try {
      const username = localStorage.getItem("auth_username") || "node"
      const password = (await loadPassword()) ?? ""
      const res = await fetch("/api/v1/logs/share", {
        method: "POST",
        headers: {
          Authorization: `Basic ${btoa(`${username}:${password}`)}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ automation_ids: Array.from(selectedIds) }),
      })
      const data = await res.json()
      if (data.success) {
        setShareCreds({ errorId: data.errorId, errorSecret: data.errorSecret })
        setShareLogsOpen(true)
      } else {
        showErrorToast(data.error ?? "Failed to share logs")
      }
    } catch {
      showErrorToast("Failed to share logs")
    } finally {
      setShareLogsLoading(false)
    }
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
            loading={shareLogsLoading}
            onClick={handleShareLogs}
          >
            Share logs
          </LoadingButton>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setDeleteOpen(true)}
          >
            <Trash2 className="size-3.5" />
            Delete
          </Button>
        </div>
      </div>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              Delete {selectedIds.size} OctoBot
              {selectedIds.size !== 1 ? "s" : ""}
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

      <Dialog open={shareLogsOpen} onOpenChange={setShareLogsOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Logs shared</DialogTitle>
            <DialogDescription>
              Share these credentials with the OctoBot team to help diagnose
              issues.
            </DialogDescription>
          </DialogHeader>
          {shareCreds && (
            <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
              <span className="font-medium text-muted-foreground">
                Error ID
              </span>
              <span className="select-all break-all font-mono text-xs">
                {shareCreds.errorId}
              </span>
              <span className="font-medium text-muted-foreground">
                Error Secret
              </span>
              <span className="select-all break-all font-mono text-xs">
                {shareCreds.errorSecret}
              </span>
            </div>
          )}
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Close</Button>
            </DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
