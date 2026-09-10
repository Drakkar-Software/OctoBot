import { clearClientStorageWithoutReload } from "@/lib/client-storage-reset"
import {
  getPriorSessionId,
  shouldReportSessionAborted,
  startBootWatchdog,
} from "@/lib/boot-watchdog"
import { reportUiJournalEvent } from "@/lib/journal-client-event"
import { reportSessionAborted } from "@/lib/shell-error-reporting"

startBootWatchdog({
  onBootTimeout: () => {
    if (shouldReportSessionAborted()) {
      reportSessionAborted(getPriorSessionId())
    }
  },
})

window.addEventListener("octobot-static-recovery-reset-requested", () => {
  void (async () => {
    await reportUiJournalEvent(
      "ui_client_storage_reset",
      {
        reset_tier: "full",
        trigger: "manual_recovery",
        recovery_attempt: 1,
      },
      { allowDuplicate: true },
    )
    await clearClientStorageWithoutReload()
    window.location.reload()
  })()
})
