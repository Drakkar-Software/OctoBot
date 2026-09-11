import { resetClientStorage } from "@/lib/client-storage-reset"
import {
  getPriorSessionId,
  shouldReportSessionAborted,
  startBootWatchdog,
} from "@/lib/boot-watchdog"
import { reportSessionAborted } from "@/lib/shell-error-reporting"

startBootWatchdog({
  onBootTimeout: () => {
    if (shouldReportSessionAborted()) {
      reportSessionAborted(getPriorSessionId())
    }
  },
})

window.addEventListener("octobot-static-recovery-reset-requested", () => {
  void resetClientStorage("manual_recovery")
})
