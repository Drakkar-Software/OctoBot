import {
  forwardRef,
  useCallback,
  useImperativeHandle,
  useState,
} from "react"

import { ExecuteActionDialog } from "@/components/Debug/dialogs/ExecuteActionDialog"
import type { ExecuteActionDraft } from "@/lib/debug/types"

export type DebugExecuteActionHandle = {
  open: (draft?: ExecuteActionDraft) => void
}

type DebugExecuteActionDialogHostProps = {
  walletAddress?: string
  onSuccess: () => void
  copyOnly: boolean
}

export const DebugExecuteActionDialogHost = forwardRef<
  DebugExecuteActionHandle,
  DebugExecuteActionDialogHostProps
>(function DebugExecuteActionDialogHost(
  { walletAddress, onSuccess, copyOnly },
  ref,
) {
  const [executeOpen, setExecuteOpen] = useState(false)
  const [executeDraft, setExecuteDraft] = useState<ExecuteActionDraft | null>(
    null,
  )

  const open = useCallback((draft?: ExecuteActionDraft) => {
    setExecuteDraft(draft ?? null)
    setExecuteOpen(true)
  }, [])

  useImperativeHandle(ref, () => ({ open }), [open])

  const handleExecuteOpenChange = (openDialog: boolean) => {
    setExecuteOpen(openDialog)
    if (!openDialog) {
      setExecuteDraft(null)
    }
  }

  return (
    <ExecuteActionDialog
      open={executeOpen}
      onOpenChange={handleExecuteOpenChange}
      walletAddress={walletAddress}
      onSuccess={onSuccess}
      draft={executeDraft}
      copyOnly={copyOnly}
    />
  )
})
