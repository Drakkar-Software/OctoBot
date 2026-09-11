import { useMutation, useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { useEffect, useState } from "react"

import { ApiError } from "@/client"
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
import { Skeleton } from "@/components/ui/skeleton"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"
import {
  downloadPreviewEnvelope,
  fetchFeedbackPreview,
  getPreviewEventCount,
  getPreviewAutomationCount,
  type ShareFeedbackContactMethod,
  type ShareFeedbackContext,
  type ShareFeedbackFailureKind,
  submitFeedbackDownload,
} from "@/lib/feedback-share"

type ShareFeedbackDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  context: ShareFeedbackContext
}

const RECOVERY_CONTEXT_LABELS: Record<ShareFeedbackFailureKind, string> = {
  boot_failed: "Recovery: boot failed",
  session_aborted: "Recovery: session aborted",
  auth_broken: "Recovery: sign-in data broken",
  fatal_render: "Recovery: fatal render error",
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
  return (
    <div className="space-y-3 rounded-md border border-border p-3">
      <p className="font-medium">Activity history</p>
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-md border border-border bg-muted/20 px-3 py-4 text-center">
          {isLoading ? (
            <Skeleton className="mx-auto h-8 w-10" />
          ) : (
            <p className="text-2xl font-semibold tabular-nums">{eventCount}</p>
          )}
          <p className="text-xs text-muted-foreground">Events</p>
        </div>
        <div className="rounded-md border border-border bg-muted/20 px-3 py-4 text-center">
          {isLoading ? (
            <Skeleton className="mx-auto h-8 w-10" />
          ) : (
            <p className="text-2xl font-semibold tabular-nums">
              {automationCount ?? "—"}
            </p>
          )}
          <p className="text-xs text-muted-foreground">Created automations</p>
        </div>
      </div>
      {isLoading ? (
        <Skeleton className="h-10 w-full" />
      ) : (
        <Button
          type="button"
          variant="outline"
          className="w-full"
          onClick={onCheckFileContentClick}
        >
          Check file content
        </Button>
      )}
      {!isLoading && isEmptyJournal && (
        <p className="text-muted-foreground">
          Nothing has been recorded yet. Use the app or trigger a recovery event,
          then try again.
        </p>
      )}
    </div>
  )
}

export function ShareFeedbackDialog({
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

  const submitMutation = useMutation({
    mutationFn: () =>
      submitFeedbackDownload({
        note,
        context,
        contactMethod: contactMethod || undefined,
        contactValue,
      }),
    onSuccess: () => {
      showSuccessToast("Feedback file downloaded")
      onOpenChange(false)
    },
    onError: (error) => {
      if (isAuthRequiredError(error)) {
        return
      }
      showErrorToast(
        error instanceof Error ? error.message : "Couldn't download feedback",
      )
    },
  })

  const preview = previewQuery.data
  const eventCount = preview ? getPreviewEventCount(preview) : null
  const automationCount = preview ? getPreviewAutomationCount(preview) : null
  const isAuthRequired =
    isAuthRequiredError(previewQuery.error) ||
    isAuthRequiredError(submitMutation.error)
  const isEmptyJournal = eventCount === 0
  const isActivityHistoryLoading = previewQuery.isLoading || !preview
  const contextChipLabel = getContextChipLabel(context)
  const showSignInLink = isAuthRequired && context.source !== "recovery"
  const contactDetailPlaceholder = contactMethod
    ? CONTACT_DETAIL_PLACEHOLDERS[contactMethod]
    : "Contact detail"

  const handleCheckFileContentClick = () => {
    if (!preview) {
      return
    }
    downloadPreviewEnvelope(preview)
    showSuccessToast("Preview file downloaded")
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
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

          {isAuthRequired && (
            <p className="text-muted-foreground">
              Sign in to send feedback.
              {showSignInLink ? (
                <>
                  {" "}
                  <Link to="/login" className="underline underline-offset-2">
                    Go to sign in
                  </Link>
                </>
              ) : null}
            </p>
          )}

          {previewQuery.isError && !isAuthRequired && (
            <p className="text-destructive">
              {previewQuery.error instanceof Error
                ? previewQuery.error.message
                : "Couldn't load feedback preview"}
            </p>
          )}

          {!isAuthRequired && !previewQuery.isError && (
            <ActivityHistorySection
              isLoading={isActivityHistoryLoading}
              eventCount={eventCount}
              automationCount={automationCount}
              isEmptyJournal={isEmptyJournal}
              onCheckFileContentClick={handleCheckFileContentClick}
            />
          )}

          {!isAuthRequired && (
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
              <div className="flex flex-col gap-1.5">
                <Label>How can we contact you? (optional)</Label>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-[9rem_minmax(0,1fr)]">
                  <Select
                    value={contactMethod}
                    onValueChange={(value) =>
                      setContactMethod(value as ShareFeedbackContactMethod)
                    }
                  >
                    <SelectTrigger className="w-full">
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
            disabled={
              isAuthRequired ||
              previewQuery.isLoading ||
              previewQuery.isError ||
              isEmptyJournal ||
              !preview
            }
            onClick={() => submitMutation.mutate()}
          >
            Send feedback
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
