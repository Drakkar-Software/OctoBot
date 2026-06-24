import { useMutation } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"
import { useState } from "react"

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

type DebugTabDeleteControlsProps = {
  deleteMode: boolean
  canDelete: boolean
  selectedCount: number
  selectedIds: Set<string>
  onEnterDeleteMode: () => void
  onCancelDeleteMode: () => void
  onDeleted: () => void
}

export function DebugTabDeleteControls({
  deleteMode,
  canDelete,
  selectedCount,
  selectedIds,
  onEnterDeleteMode,
  onCancelDeleteMode,
  onDeleted,
}: DebugTabDeleteControlsProps) {
  const [confirmOpen, setConfirmOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const deleteMutation = useMutation({
    mutationFn: () =>
      TasksService.deleteTasks({
        taskIds: Array.from(selectedIds),
      }),
    onSuccess: () => {
      showSuccessToast(
        `Deleted ${selectedCount} item${selectedCount !== 1 ? "s" : ""}`,
      )
      setConfirmOpen(false)
      onDeleted()
    },
    onError: () => {
      showErrorToast("Some deletions failed")
    },
  })

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        {deleteMode && (
          <Button
            variant="destructive"
            size="sm"
            disabled={selectedCount === 0}
            onClick={() => setConfirmOpen(true)}
          >
            <Trash2 className="size-4" />
            Delete selected elements
          </Button>
        )}
        {deleteMode ? (
          <Button variant="outline" size="sm" onClick={onCancelDeleteMode}>
            Cancel
          </Button>
        ) : (
          <Button
            variant="outline"
            size="sm"
            disabled={!canDelete}
            onClick={onEnterDeleteMode}
          >
            <Trash2 className="size-4" />
            Delete
          </Button>
        )}
      </div>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              Delete {selectedCount} selected item
              {selectedCount !== 1 ? "s" : ""}
            </DialogTitle>
            <DialogDescription>
              This will permanently delete the selected items that are no longer
              running. Running workflows will not be deleted. This action cannot
              be undone.
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
    </>
  )
}
