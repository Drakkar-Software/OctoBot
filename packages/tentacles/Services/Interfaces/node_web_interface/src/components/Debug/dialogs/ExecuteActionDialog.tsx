import { useMutation } from "@tanstack/react-query"
import { Copy } from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import { type ApiError, DebugService, type UserAction } from "@/client"
import { Button } from "@/components/ui/button"
import { LineNumberTextarea } from "@/components/ui/line-number-textarea"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"
import { copyTextToClipboard } from "@/lib/clipboard"
import type { ExecuteActionDraft } from "@/lib/debug/types"
import { validateUserActionJson } from "@/lib/debug/user-action"
import {
  buildUserActionTemplateJson,
  DEFAULT_USER_ACTION_TEMPLATE_KEY,
  USER_ACTION_TEMPLATE_OPTIONS,
  type UserActionTemplateKey,
  userActionTemplateKeyFromActionType,
} from "@/lib/debug/user-action-templates"
import { handleError } from "@/utils"

type ExecuteActionDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  walletAddress?: string
  onSuccess: () => void
  draft: ExecuteActionDraft | null
  copyOnly?: boolean
}

export function ExecuteActionDialog({
  open,
  onOpenChange,
  walletAddress,
  onSuccess,
  draft,
  copyOnly = false,
}: ExecuteActionDialogProps) {
  const [selectedTemplateKey, setSelectedTemplateKey] =
    useState<UserActionTemplateKey>(DEFAULT_USER_ACTION_TEMPLATE_KEY)
  const [jsonText, setJsonText] = useState(() =>
    buildUserActionTemplateJson(DEFAULT_USER_ACTION_TEMPLATE_KEY),
  )
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const validationError = useMemo(
    () => validateUserActionJson(jsonText),
    [jsonText],
  )

  useEffect(() => {
    if (open) {
      if (draft) {
        setSelectedTemplateKey(userActionTemplateKeyFromActionType(draft.actionType))
        setJsonText(draft.jsonText)
      } else {
        setSelectedTemplateKey(DEFAULT_USER_ACTION_TEMPLATE_KEY)
        setJsonText(buildUserActionTemplateJson(DEFAULT_USER_ACTION_TEMPLATE_KEY))
      }
    }
  }, [open, draft])

  const handleTemplateKeyChange = (value: UserActionTemplateKey) => {
    setSelectedTemplateKey(value)
    setJsonText(buildUserActionTemplateJson(value))
  }

  const mutation = useMutation({
    mutationFn: (body: UserAction) =>
      DebugService.executeUserAction({
        requestBody: body,
        walletAddress: walletAddress ?? null,
      }),
    onSuccess: () => {
      showSuccessToast("Action submitted")
      onOpenChange(false)
      onSuccess()
    },
    onError: (error) => {
      handleError.bind(showErrorToast)(error as ApiError)
    },
  })

  const handleRun = () => {
    if (validationError) return
    const parsed = JSON.parse(jsonText.trim()) as UserAction
    mutation.mutate(parsed)
  }

  const handleCopy = () => {
    if (validationError) return
    copyTextToClipboard(jsonText.trim(), "User action JSON")
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {copyOnly ? "User action" : "Execute user action"}
          </DialogTitle>
          <DialogDescription>
            {copyOnly
              ? "Edit the JSON below if needed, then copy it for the user to run on their node."
              : "POST a UserAction JSON body to the debug endpoint."}
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          {!copyOnly && (
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Action type
              </label>
              <Select
                value={selectedTemplateKey}
                onValueChange={(value) =>
                  handleTemplateKeyChange(value as UserActionTemplateKey)
                }
              >
                <SelectTrigger size="sm" className="w-full max-w-none">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {USER_ACTION_TEMPLATE_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          <LineNumberTextarea
            value={jsonText}
            onChange={(event) => setJsonText(event.target.value)}
          />
        </div>
        {validationError && (
          <p className="text-sm text-destructive">{validationError}</p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          {copyOnly ? (
            <Button onClick={handleCopy} disabled={validationError !== null}>
              <Copy className="size-4" />
              Copy
            </Button>
          ) : (
            <Button
              onClick={handleRun}
              disabled={mutation.isPending || validationError !== null}
            >
              {mutation.isPending ? "Running…" : "Run"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
