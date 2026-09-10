import { reportUiJournalEvent } from "@/lib/journal-client-event"
import { DEVICE_DATABASE_NAME } from "@/lib/ui-recovery-constants"

export type ResetTrigger = "manual_recovery" | "manual_settings"

function deleteDeviceDatabase(): Promise<void> {
  return new Promise((resolve, reject) => {
    const deleteRequest = indexedDB.deleteDatabase(DEVICE_DATABASE_NAME)
    deleteRequest.onsuccess = () => resolve()
    deleteRequest.onerror = () => reject(deleteRequest.error)
    deleteRequest.onblocked = () => resolve()
  })
}

export async function resetClientStorage(trigger: ResetTrigger): Promise<void> {
  await reportUiJournalEvent(
    "ui_client_storage_reset",
    {
      reset_tier: "full",
      trigger,
      recovery_attempt: 1,
    },
    { allowDuplicate: true },
  )
  localStorage.clear()
  sessionStorage.clear()
  await deleteDeviceDatabase()
  window.location.reload()
}

export async function clearClientStorageWithoutReload(): Promise<void> {
  localStorage.clear()
  sessionStorage.clear()
  await deleteDeviceDatabase()
}
