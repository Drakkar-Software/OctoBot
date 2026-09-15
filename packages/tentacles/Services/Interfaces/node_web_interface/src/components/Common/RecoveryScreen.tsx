import { useState } from "react"

import { InsecureContextGuidance } from "@/components/Common/InsecureContextGuidance"
import { ShareFeedbackButton } from "@/components/Common/ShareFeedbackButton"
import { TailscaleRemoteAccessDialog } from "@/components/Common/TailscaleRemoteAccessDialog"
import { resetClientStorage } from "@/lib/client-storage-reset"
import {
  INSECURE_CONTEXT_HEADING,
  RECOVERY_EXPLANATION,
  RESET_CONFIRM_MESSAGE,
} from "@/lib/ui-recovery-constants"
import { Button } from "@/components/ui/button"

export type RecoveryFailureKind =
  | "boot_failed"
  | "auth_broken"
  | "fatal_render"
  | "insecure_context"

const FAILURE_HEADINGS: Record<RecoveryFailureKind, string> = {
  boot_failed: "OctoBot Node failed to start",
  auth_broken: "Sign-in data is inconsistent",
  fatal_render: "OctoBot Node encountered a fatal error",
  insecure_context: INSECURE_CONTEXT_HEADING,
}

type RecoveryScreenProps = {
  failureKind: RecoveryFailureKind
}

export function confirmAndResetLocalBrowserData(
  confirmFn: () => boolean = () => window.confirm(RESET_CONFIRM_MESSAGE),
): void {
  if (!confirmFn()) {
    return
  }
  void resetClientStorage("manual_recovery")
}

export function RecoveryScreen({ failureKind }: RecoveryScreenProps) {
  const [tailscaleDialogOpen, setTailscaleDialogOpen] = useState(false)

  const handleResetClick = () => {
    confirmAndResetLocalBrowserData()
  }

  const handleReloadClick = () => {
    window.location.reload()
  }

  const isInsecureContext = failureKind === "insecure_context"
  const explanation = isInsecureContext ? null : RECOVERY_EXPLANATION
  const feedbackContext = { source: "recovery" as const, failureKind }

  return (
    <div
      className="flex min-h-screen items-center justify-center p-4"
      data-testid="recovery-screen"
    >
      <div className="max-w-lg space-y-4 rounded-lg border border-border bg-card p-6 shadow-sm">
        <h1 className="text-xl font-semibold">{FAILURE_HEADINGS[failureKind]}</h1>
        {isInsecureContext ? (
          <>
            <InsecureContextGuidance
              onSetUpRemoteAccessClick={() => setTailscaleDialogOpen(true)}
            />
            <div
              className="flex justify-end"
              data-testid="recovery-insecure-share-feedback"
            >
              <ShareFeedbackButton context={feedbackContext} />
            </div>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">{explanation}</p>
        )}
        {!isInsecureContext ? (
          <div className="flex flex-wrap gap-3">
            <Button type="button" onClick={handleResetClick}>
              Reset local browser data
            </Button>
            <Button type="button" variant="outline" onClick={handleReloadClick}>
              Reload page
            </Button>
            <ShareFeedbackButton context={feedbackContext} />
          </div>
        ) : null}
      </div>
      {isInsecureContext ? (
        <TailscaleRemoteAccessDialog
          open={tailscaleDialogOpen}
          onOpenChange={setTailscaleDialogOpen}
        />
      ) : null}
    </div>
  )
}
