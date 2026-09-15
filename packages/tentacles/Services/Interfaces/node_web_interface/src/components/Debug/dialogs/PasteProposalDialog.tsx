import {
  type ActionProposal,
  describeProposedAction,
  type ProposedActionEntry,
} from "@drakkar.software/octobot-client/protocol"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import { type ApiError, DebugService } from "@/client"
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
import useCustomToast from "@/hooks/useCustomToast"
import {
  type ParsedProposal,
  type ProposalStepState,
  parseProposalText,
  runActionProposal,
} from "@/lib/debug/action-proposal"
import { cn } from "@/lib/utils"
import { extractErrorMessage } from "@/utils"

type StepDisplay = { state: ProposalStepState; detail?: string }

const STEP_STATUS_DISPLAY: Record<
  ProposalStepState,
  { emoji: string; label: string; pulse?: boolean }
> = {
  waiting: { emoji: "⚪", label: "Waiting" },
  submitting: { emoji: "🟡", label: "Submitting", pulse: true },
  running: { emoji: "🟢", label: "Running", pulse: true },
  completed: { emoji: "✅", label: "Completed" },
  failed: { emoji: "🔴", label: "Failed" },
  skipped: { emoji: "⚪", label: "Skipped" },
}

function parseErrorMessage(
  parsed: Extract<ParsedProposal, { ok: false }>,
): string | null {
  switch (parsed.reason) {
    case "empty":
      return null
    case "frame":
      return "That's one frame of a QR code, not the whole proposal. Use Copy proposal in the app instead."
    case "unsupported-version":
      return "This proposal came from a newer OctoBot app. Update this node to run it."
    case "invalid":
      return parsed.detail
        ? `This isn't an action proposal.\n${parsed.detail}`
        : "This isn't an action proposal."
  }
}

function describeSubmitError(error: unknown): string {
  // 404 here specifically means "the debug routes are off" (see
  // _ensure_debug_routes_enabled on the node) — everything else reuses the
  // same body.detail extraction the rest of the debug view already has.
  if ((error as { status?: number } | undefined)?.status === 404) {
    return "Debug actions are turned off while node-side encryption is on."
  }
  return extractErrorMessage(error as ApiError)
}

type PasteProposalDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  walletAddress?: string
  onSuccess: () => void
}

export function PasteProposalDialog({
  open,
  onOpenChange,
  walletAddress,
  onSuccess,
}: PasteProposalDialogProps) {
  const [jsonText, setJsonText] = useState("")
  const [phase, setPhase] = useState<"paste" | "running">("paste")
  const [steps, setSteps] = useState<StepDisplay[]>([])
  const abortRef = useRef<AbortController | null>(null)
  const { showSuccessToast } = useCustomToast()

  const parsed = useMemo(() => parseProposalText(jsonText), [jsonText])
  // Every rejection path in runActionProposal marks its own step "failed"
  // before throwing, so "the run failed" is always exactly "some step is in
  // the failed state" — no separate flag to keep in sync with it.
  const runFailed = steps.some((step) => step.state === "failed")

  useEffect(() => {
    if (open) {
      // A proposal can carry account_auth_create/edit with plaintext
      // credentials — never carry it across dialog opens.
      setJsonText("")
      setPhase("paste")
      setSteps([])
    } else {
      abortRef.current?.abort()
    }
  }, [open])

  const submit = useCallback(
    async ({
      id,
      configuration,
    }: {
      id: string
      configuration: ProposedActionEntry["configuration"]
    }) => {
      try {
        await DebugService.executeUserAction({
          requestBody: { id, configuration },
          walletAddress: walletAddress ?? null,
        })
      } catch (error) {
        throw new Error(describeSubmitError(error))
      }
    },
    [walletAddress],
  )

  const fetchDebugState = useCallback(
    () => DebugService.getDebug(walletAddress ? { walletAddress } : {}),
    [walletAddress],
  )

  const handleRun = (proposal: ActionProposal) => {
    setSteps(proposal.actions.map(() => ({ state: "waiting" })))
    setPhase("running")

    const controller = new AbortController()
    abortRef.current = controller

    runActionProposal(proposal, {
      submit,
      fetchDebugState,
      signal: controller.signal,
      onStep: (index, state, detail) => {
        setSteps((prev) => {
          const next = [...prev]
          next[index] = { state, detail }
          return next
        })
      },
    })
      .then(() => {
        // Closing the dialog aborts the run, and an aborted run resolves
        // rather than rejects (an intentional stop is not a failure) — so a
        // resolved promise here does not always mean every step completed.
        // Also guard against a stale run: the dialog persists across opens,
        // so a run from a previous session settling late must not touch
        // state for whatever is running now.
        if (controller.signal.aborted || abortRef.current !== controller) return
        showSuccessToast("Proposal completed")
        onSuccess()
      })
      // Nothing left to do on rejection — the failing step already recorded
      // itself via onStep before runActionProposal rethrew. This catch only
      // exists so the rejection doesn't surface as unhandled.
      .catch(() => {})
  }

  const errorMessage = !parsed.ok ? parseErrorMessage(parsed) : null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[85vh] max-w-2xl flex-col">
        <DialogHeader className="shrink-0">
          <DialogTitle>Paste a proposal</DialogTitle>
          <DialogDescription>
            Your phone made this action but could not send it. Paste it here to
            run it on this node.
          </DialogDescription>
        </DialogHeader>

        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto">
          {phase === "paste" ? (
            <>
              <LineNumberTextarea
                className="min-h-[220px] shrink-0"
                textareaClassName="min-h-[220px]"
                value={jsonText}
                onChange={(event) => setJsonText(event.target.value)}
              />
              {errorMessage && (
                <div
                  role="alert"
                  className="whitespace-pre-wrap rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
                >
                  {errorMessage}
                </div>
              )}
              {parsed.ok && (
                <div className="flex flex-col gap-2 rounded-md border p-3">
                  {parsed.proposal.label && (
                    <p className="text-sm font-medium">
                      {parsed.proposal.label}
                    </p>
                  )}
                  {parsed.proposal.actions.map((entry, index) => (
                    <p key={index} className="text-sm text-muted-foreground">
                      {describeProposedAction(entry.configuration)}
                    </p>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="flex flex-col gap-1">
              {steps.map((step, index) => {
                const entry = (
                  parsed.ok ? parsed.proposal.actions[index] : undefined
                ) as ProposedActionEntry | undefined
                if (!entry) return null
                const display = STEP_STATUS_DISPLAY[step.state]
                const chained = entry.after === "previous-confirmed"
                return (
                  <div key={index} className="flex flex-col">
                    {chained && (
                      <div
                        className="ml-[7px] h-3 w-px bg-border"
                        aria-hidden
                      />
                    )}
                    <div className="flex items-start gap-2">
                      <span
                        role="img"
                        aria-label={display.label}
                        className={cn(
                          "text-sm leading-5",
                          display.pulse && "animate-pulse",
                        )}
                      >
                        {display.emoji}
                      </span>
                      <div className="flex min-w-0 flex-col">
                        <p className="text-sm">
                          {describeProposedAction(entry.configuration)}
                        </p>
                        {chained && (
                          <p className="text-xs text-muted-foreground">
                            Waits for step {index}
                          </p>
                        )}
                        {step.state === "failed" && step.detail && (
                          <p className="text-xs text-destructive">
                            {step.detail}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
              {runFailed && (
                <p className="mt-2 text-sm text-destructive">
                  This proposal didn't finish. See the failed step above.
                </p>
              )}
            </div>
          )}
        </div>

        <DialogFooter className="shrink-0">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {phase === "running" ? "Close" : "Cancel"}
          </Button>
          {phase === "paste" && (
            <Button
              onClick={() => parsed.ok && handleRun(parsed.proposal)}
              disabled={!parsed.ok}
            >
              Run proposal
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
