import { useMutation, useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { useEffect, useState } from "react"

import { ApiError } from "@/client"
import { AuthLoginRedirectSuppressionProvider } from "@/components/Common/AuthLoginRedirectSuppressionProvider"
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
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"
import {
  computeShareFeedbackSendDisabled,
  downloadPreviewEnvelope,
  fetchFeedbackPreview,
  getPreviewEventCount,
  getPreviewAutomationCount,
  getShareFeedbackUiErrorName,
  submitFeedbackDownload,
  type ShareFeedbackContactMethod,
  type ShareFeedbackContext,
  type ShareFeedbackFailureKind,
} from "@/lib/feedback-share"
import { FEEDBACK_EMPTY_JOURNAL_HINT } from "@/lib/ui-recovery-constants"

type ShareFeedbackDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  context: ShareFeedbackContext
}

const RECOVERY_CONTEXT_LABELS: Record<ShareFeedbackFailureKind, string> = {
  boot_failed: "Recovery: boot failed",
  auth_broken: "Recovery: sign-in data broken",
  fatal_render: "Recovery: fatal render error",
  insecure_context: "Recovery: insecure browser context",
}

const CONTACT_METHOD_OPTIONS: Array<{
  value: ShareFeedbackContactMethod
  label: string
}> = [
  { value: "email", label: "Email" },
  { value: "telegram", label: "Telegram" },
  { value: "discord", label: "Discord" },
]

const CONTACT_DETAIL_PLACEHOLDERS: Record<ShareFeedbackContactMethod, string> = {
  email: "you@example.com",
  telegram: "@username",
  discord: "username",
}

function getContextChipLabel(context: ShareFeedbackContext): string | null {
  if (context.source === "recovery") {
    return RECOVERY_CONTEXT_LABELS[context.failureKind]
  }
  if (context.source === "route_error") {
    return context.routePath
      ? `Route error: ${context.routePath}`
      : "Route error"
  }
  return null
}

function isAuthRequiredError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}

type ActivityHistorySectionProps = {
  isLoading: boolean
  eventCount: number | null
  automationCount: number | null
  isEmptyJournal: boolean
  onCheckFileContentClick: () => void
}

function ActivityHistorySection({
  isLoading,
  eventCount,
  automationCount,
  isEmptyJournal,
  onCheckFileContentClick,
}: ActivityHistorySectionProps) {
  const displayEventCount = isLoading ? 0 : eventCount
  const displayAutomationCount = isLoading ? 0 : automationCount

  return (
    <div className="space-y-3 rounded-md border border-border p-3">
      <p className="font-medium">Activity history</p>
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-md border border-border bg-muted/20 px-3 py-4 text-center">
          <p className="text-2xl font-semibold tabular-nums">{displayEventCount}</p>
          <p className="text-xs text-muted-foreground">Events</p>
        </div>
        <div className="rounded-md border border-border bg-muted/20 px-3 py-4 text-center">
          <p className="text-2xl font-semibold tabular-nums">
            {displayAutomationCount ?? "—"}
          </p>
          <p className="text-xs text-muted-foreground">Created automations</p>
        </div>
      </div>
      <Button
        type="button"
        variant="outline"
        className="w-full"
        disabled={isLoading}
        onClick={onCheckFileContentClick}
      >
        Check file content
      </Button>
      {!isLoading && isEmptyJournal && (
        <p className="text-muted-foreground">{FEEDBACK_EMPTY_JOURNAL_HINT}</p>
      )}
    </div>
  )
}

export function ShareFeedbackDialogContent({
  open,
  onOpenChange,
  context,
}: ShareFeedbackDialogProps) {
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const [note, setNote] = useState("")
  const [contactMethod, setContactMethod] = useState<
    ShareFeedbackContactMethod | ""
  >("")
  const [contactValue, setContactValue] = useState("")
  const hasUiErrorContext = getShareFeedbackUiErrorName(context) !== null

  const previewQuery = useQuery({
    queryKey: ["feedback-preview"],
    queryFn: fetchFeedbackPreview,
    enabled: open,
    retry: false,
  })

  useEffect(() => {
    if (!open) {
      setNote("")
      setContactMethod("")
      setContactValue("")
    }
  }, [open])

  const isRecoveryContext = context.source === "recovery"
  const previewAuthBlocked = isAuthRequiredError(previewQuery.error)
  const useDegradedRecoveryFeedback =
    isRecoveryContext && previewAuthBlocked
  const showSignInPrompt = previewAuthBlocked && !isRecoveryContext

  const submitMutation = useMutation({
    mutationFn: () =>
      submitFeedbackDownload({
        note,
        context,
        contactMethod: contactMethod || undefined,
        contactValue,
      }),
    onSuccess: () => {
      showSuccessToast(
        "Journal downloaded. Finish sending in your email app.",
      )
      onOpenChange(false)
    },
    onError: (error) => {
      showErrorToast(
        error instanceof Error ? error.message : "Couldn't export feedback",
      )
    },
  })

  const preview = previewQuery.data
  const eventCount = preview ? getPreviewEventCount(preview) : null
  const automationCount = preview ? getPreviewAutomationCount(preview) : null
  const isEmptyJournal = eventCount === 0
  const isActivityHistoryLoading = previewQuery.isLoading || !preview
  const contextChipLabel = getContextChipLabel(context)
  const contactDetailPlaceholder = contactMethod
    ? CONTACT_DETAIL_PLACEHOLDERS[contactMethod]
    : "Contact detail"

  const showActivityHistory =
    !useDegradedRecoveryFeedback &&
    !showSignInPrompt &&
    (previewQuery.isLoading || previewQuery.isSuccess)
  const showPreviewLoadError =
    previewQuery.isError &&
    !previewAuthBlocked &&
    !useDegradedRecoveryFeedback
  const showFeedbackForm = !showSignInPrompt

  const isSendDisabled = computeShareFeedbackSendDisabled({
    submitPending: submitMutation.isPending,
    useDegradedRecoveryFeedback,
    hasUiErrorContext,
    showSignInPrompt,
    previewLoading: previewQuery.isLoading,
    previewError: previewQuery.isError,
    hasPreview: Boolean(preview),
    eventCount,
    note,
  })

  const handleCheckFileContentClick = () => {
    if (!preview) {
      return
    }
    downloadPreviewEnvelope(preview)
    showSuccessToast("Journal preview downloaded")
  }

  return (
    <DialogContent className="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>Help us improve OctoBot</DialogTitle>
        <DialogDescription>
          Your feedback helps us make OctoBot better. Tell us what&apos;s
          working, what&apos;s confusing, or what went wrong. We&apos;ll
          attach anonymised diagnostics so the team can understand what
          happened.
        </DialogDescription>
      </DialogHeader>

      <div className="flex flex-col gap-4 text-sm">
        <div className="space-y-2">
          <p className="font-medium">What will be shared</p>
          <div className="rounded-md border border-border bg-muted/30 px-3 py-2 text-muted-foreground">
            <ul className="list-disc space-y-1 pl-4">
              <li>Diagnostic events (steps, errors, UI issues)</li>
              <li>App version and anonymous install ID</li>
            </ul>
            <p className="mt-2">
              Excludes API keys, trading data, and personal information.
            </p>
          </div>
        </div>

        {contextChipLabel && (
          <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
            {contextChipLabel}
          </p>
        )}

        {showSignInPrompt && (
          <p className="text-muted-foreground">
            Sign in to send feedback.{" "}
            <Link to="/login" className="underline underline-offset-2">
              Go to sign in
            </Link>
          </p>
        )}

        {showPreviewLoadError && (
          <p className="text-destructive">
            {previewQuery.error instanceof Error
              ? previewQuery.error.message
              : "Couldn't load feedback preview"}
          </p>
        )}

        {showActivityHistory && (
          <ActivityHistorySection
            isLoading={isActivityHistoryLoading}
            eventCount={eventCount}
            automationCount={automationCount}
            isEmptyJournal={isEmptyJournal}
            onCheckFileContentClick={handleCheckFileContentClick}
          />
        )}

        {showFeedbackForm && (
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="feedback-note">Your feedback (optional)</Label>
              <textarea
                id="feedback-note"
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Describe your feedback or issue with as much details as possible"
                rows={4}
                className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>
            <div className="flex flex-col gap-1">
              <Label>How can we contact you? (optional)</Label>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-[9rem_minmax(0,1fr)]">
                <Select
                  value={contactMethod}
                  onValueChange={(value) =>
                    setContactMethod(value as ShareFeedbackContactMethod)
                  }
                >
                  <SelectTrigger size="sm" className="w-full px-3">
                    <SelectValue placeholder="Method" />
                  </SelectTrigger>
                  <SelectContent>
                    {CONTACT_METHOD_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  id="feedback-contact-value"
                  value={contactValue}
                  onChange={(event) => setContactValue(event.target.value)}
                  placeholder={contactDetailPlaceholder}
                  className="h-9 text-sm"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      <DialogFooter>
        <DialogClose asChild>
          <Button
            type="button"
            variant="outline"
            disabled={submitMutation.isPending}
          >
            Cancel
          </Button>
        </DialogClose>
        <LoadingButton
          type="button"
          loading={submitMutation.isPending}
          disabled={isSendDisabled}
          onClick={() => submitMutation.mutate()}
        >
          Download & email
        </LoadingButton>
      </DialogFooter>
    </DialogContent>
  )
}

export function ShareFeedbackDialog({
  open,
  onOpenChange,
  context,
}: ShareFeedbackDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {open && context.source === "recovery" ? (
        <AuthLoginRedirectSuppressionProvider>
          <ShareFeedbackDialogContent
            open={open}
            onOpenChange={onOpenChange}
            context={context}
          />
        </AuthLoginRedirectSuppressionProvider>
      ) : open ? (
        <ShareFeedbackDialogContent
          open={open}
          onOpenChange={onOpenChange}
          context={context}
        />
      ) : null}
    </Dialog>
  )
}
