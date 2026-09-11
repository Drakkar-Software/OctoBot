import { clearAllDeviceRecords } from "@/lib/device-key"
import { reportUiJournalEvent } from "@/lib/journal-client-event"

export type ResetTrigger = "manual_recovery" | "manual_settings"

function buildResetJournalAttributes(trigger: ResetTrigger) {
  return {
    reset_tier: "full",
    auth_preserved: false,
    trigger,
    recovery_attempt: 1,
  }
}

export async function clearClientStorageWithoutReload(): Promise<void> {
  localStorage.clear()
  sessionStorage.clear()
  await clearAllDeviceRecords()
}

export async function resetClientStorage(trigger: ResetTrigger): Promise<void> {
  await reportUiJournalEvent(
    "ui_client_storage_reset",
    buildResetJournalAttributes(trigger),
    { allowDuplicate: true },
  )
  await clearClientStorageWithoutReload()
  window.location.reload()
}
