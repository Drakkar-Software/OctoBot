import { useMutation } from "@tanstack/react-query"
import { useEffect, useState } from "react"

import {
  type ApiError,
  type AutomationSignalType,
  type AutomationState,
  DebugService,
  type UserAction,
} from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LineNumberTextarea } from "@/components/ui/line-number-textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"
import {
  signalTypeRequiresPayload,
  validateAutomationCanReceiveSignal,
} from "@/lib/debug/automation"
import { SIGNAL_TYPE_OPTIONS } from "@/lib/debug/constants"
import { buildSignalUserActionConfiguration } from "@/lib/debug/execute-user-action"
import { defaultSignalPayloadText } from "@/lib/debug/user-action-templates"
import { handleError } from "@/utils"

type SignalAutomationDialogProps = {
  automation: AutomationState | null
  open: boolean
  onOpenChange: (open: boolean) => void
  walletAddress?: string
  onSuccess: () => void
}

export function SignalAutomationDialog({
  automation,
  open,
  onOpenChange,
  walletAddress,
  onSuccess,
}: SignalAutomationDialogProps) {
  const [signalType, setSignalType] =
    useState<AutomationSignalType>("forced_trigger")
  const [payloadText, setPayloadText] = useState("")
  const [parseError, setParseError] = useState<string | null>(null)
  const { showSuccessToast, showErrorToast } = useCustomToast()

  useEffect(() => {
    if (open) {
      setSignalType("forced_trigger")
      setPayloadText("")
      setParseError(null)
    }
  }, [open])

  const mutation = useMutation({
    mutationFn: (body: UserAction) =>
      DebugService.executeUserAction({
        requestBody: body,
        walletAddress: walletAddress ?? null,
      }),
    onSuccess: () => {
      showSuccessToast("Signal submitted")
      onOpenChange(false)
      onSuccess()
    },
    onError: (error) => {
      handleError.bind(showErrorToast)(error as ApiError)
    },
  })

  const handleSignalTypeChange = (value: AutomationSignalType) => {
    setSignalType(value)
    setParseError(null)
    if (signalTypeRequiresPayload(value)) {
      setPayloadText(defaultSignalPayloadText(value))
    }
  }

  const handleSend = () => {
    if (!automation) return
    const validationError = validateAutomationCanReceiveSignal(automation)
    if (validationError) {
      setParseError(validationError)
      return
    }
    const buildResult = buildSignalUserActionConfiguration(
      automation.id,
      signalType,
      payloadText,
    )
    if ("error" in buildResult) {
      setParseError(buildResult.error)
      return
    }
    setParseError(null)
    mutation.mutate({
      id: `ua-signal-${Date.now()}`,
      configuration: buildResult.configuration,
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Send automation signal</DialogTitle>
          <DialogDescription>
            {automation ? (
              <>
                <span className="font-medium text-foreground">
                  {automation.metadata.name}
                </span>
                <span className="font-mono text-xs block mt-1">
                  {automation.id}
                </span>
              </>
            ) : null}
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <p className="text-xs font-medium text-muted-foreground">
              Signal type
            </p>
            <Select
              value={signalType}
              onValueChange={(value) =>
                handleSignalTypeChange(value as AutomationSignalType)
              }
            >
              <SelectTrigger size="sm" className="w-full max-w-none">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SIGNAL_TYPE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {signalType === "forced_trigger" && (
              <p className="text-xs text-muted-foreground">
                No payload for forced trigger.
              </p>
            )}
          </div>
          {signalTypeRequiresPayload(signalType) && (
            <div className="flex flex-col gap-1.5">
              <p className="text-xs font-medium text-muted-foreground">
                Signal payload (JSON)
              </p>
              <LineNumberTextarea
                className="min-h-[180px]"
                textareaClassName="min-h-[180px]"
                value={payloadText}
                onChange={(event) => {
                  setPayloadText(event.target.value)
                  setParseError(null)
                }}
              />
            </div>
          )}
          {parseError && (
            <p className="text-sm text-destructive">{parseError}</p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSend} disabled={mutation.isPending}>
            {mutation.isPending ? "Sending…" : "Send"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
