import { useMutation } from "@tanstack/react-query"
import { Copy, TriangleAlert } from "lucide-react"
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
function getApiErrorMessage(error: ApiError): string {
  const errorDetail = (error.body as { detail?: unknown } | undefined)?.detail
  if (typeof errorDetail === "string" && errorDetail.length > 0) {
    return errorDetail
  }
  if (Array.isArray(errorDetail) && errorDetail.length > 0) {
    const firstDetail = errorDetail[0] as { msg?: string }
    if (firstDetail.msg) return firstDetail.msg
  }
  return error.message || "Something went wrong."
}

function ExecuteActionDialogError({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="flex max-h-32 shrink-0 items-start gap-2 overflow-y-auto rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
    >
      <TriangleAlert className="mt-0.5 size-4 shrink-0" />
      <p className="min-w-0 whitespace-pre-wrap break-words">{message}</p>
    </div>
  )
}

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
  const [submitError, setSubmitError] = useState<string | null>(null)
  const { showSuccessToast } = useCustomToast()

  const validationError = useMemo(
    () => validateUserActionJson(jsonText),
    [jsonText],
  )
  const displayedError = validationError ?? submitError

  useEffect(() => {
    if (open) {
      setSubmitError(null)
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
    setSubmitError(null)
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
      setSubmitError(getApiErrorMessage(error as ApiError))
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
      <DialogContent className="flex max-h-[85vh] max-w-2xl flex-col">
        <DialogHeader className="shrink-0">
          <DialogTitle>
            {copyOnly ? "User action" : "Execute user action"}
          </DialogTitle>
          <DialogDescription>
            {copyOnly
              ? "Edit the JSON below if needed, then copy it for the user to run on their node."
              : "POST a UserAction JSON body to the debug endpoint."}
          </DialogDescription>
        </DialogHeader>
        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto">
          {!copyOnly && (
            <div className="flex shrink-0 flex-col gap-1.5">
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
            className="min-h-[220px] shrink-0"
            textareaClassName="min-h-[220px]"
            value={jsonText}
            onChange={(event) => {
              setSubmitError(null)
              setJsonText(event.target.value)
            }}
          />
        </div>
        {displayedError && <ExecuteActionDialogError message={displayedError} />}
        <DialogFooter className="shrink-0">
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
