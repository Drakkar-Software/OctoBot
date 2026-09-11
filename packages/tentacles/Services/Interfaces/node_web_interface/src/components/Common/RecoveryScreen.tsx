import { ShareFeedbackButton } from "@/components/Common/ShareFeedbackButton"
import { resetClientStorage } from "@/lib/client-storage-reset"
import {
  RECOVERY_EXPLANATION,
  RESET_CONFIRM_MESSAGE,
} from "@/lib/ui-recovery-constants"
import { Button } from "@/components/ui/button"

export type RecoveryFailureKind =
  | "boot_failed"
  | "session_aborted"
  | "auth_broken"
  | "fatal_render"

const FAILURE_HEADINGS: Record<RecoveryFailureKind, string> = {
  boot_failed: "OctoBot Node failed to start",
  session_aborted: "Previous session ended unexpectedly",
  auth_broken: "Sign-in data is inconsistent",
  fatal_render: "OctoBot Node encountered a fatal error",
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
  const handleResetClick = () => {
    confirmAndResetLocalBrowserData()
  }

  const handleReloadClick = () => {
    window.location.reload()
  }

  return (
    <div
      className="flex min-h-screen items-center justify-center p-4"
      data-testid="recovery-screen"
    >
      <div className="max-w-lg space-y-4 rounded-lg border border-border bg-card p-6 shadow-sm">
        <h1 className="text-xl font-semibold">{FAILURE_HEADINGS[failureKind]}</h1>
        <p className="text-sm text-muted-foreground">{RECOVERY_EXPLANATION}</p>
        <div className="flex flex-wrap gap-3">
          <Button type="button" onClick={handleResetClick}>
            Reset local browser data
          </Button>
          <Button type="button" variant="outline" onClick={handleReloadClick}>
            Reload page
          </Button>
          <ShareFeedbackButton
            context={{ source: "recovery", failureKind }}
          />
        </div>
      </div>
    </div>
  )
}
