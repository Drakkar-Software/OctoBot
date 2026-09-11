import { OpenAPI } from "@/client"

export type UiJournalEvent =
  | "ui_boot_failed"
  | "ui_session_aborted"
  | "ui_auth_state_broken"
  | "ui_fatal_render_error"
  | "ui_client_storage_reset"
  | "ui_insecure_context"

export type UiJournalEventAttributes = Record<
  string,
  string | number | boolean | null
>

const CLIENT_INSTANCE_ID_KEY = "octobot_client_instance_id"
const JOURNAL_DEDUPE_PREFIX = "octobot_journal_emitted:"

function createClientInstanceId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID()
  }
  return `client-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function getOrCreateClientInstanceId(): string {
  const existingId = sessionStorage.getItem(CLIENT_INSTANCE_ID_KEY)
  if (existingId) {
    return existingId
  }
  const clientInstanceId = createClientInstanceId()
  sessionStorage.setItem(CLIENT_INSTANCE_ID_KEY, clientInstanceId)
  return clientInstanceId
}

export function getUiBuild(): string {
  return __APP_VERSION__
}

export function resolveJournalApiBase(): string {
  return OpenAPI.BASE
}

export function buildJournalClientEventUrl(apiBase: string): string {
  const normalizedBase = apiBase.endsWith("/") ? apiBase.slice(0, -1) : apiBase
  return `${normalizedBase}/api/v1/journal/client-event`
}

function shouldSkipDuplicateEvent(event: UiJournalEvent): boolean {
  const dedupeKey = `${JOURNAL_DEDUPE_PREFIX}${event}`
  if (sessionStorage.getItem(dedupeKey)) {
    return true
  }
  sessionStorage.setItem(dedupeKey, "1")
  return false
}

export async function reportUiJournalEvent(
  event: UiJournalEvent,
  attributes?: UiJournalEventAttributes,
  options?: { allowDuplicate?: boolean },
): Promise<void> {
  if (!options?.allowDuplicate && shouldSkipDuplicateEvent(event)) {
    return
  }
  try {
    const requestBody = {
      event,
      client_instance_id: getOrCreateClientInstanceId(),
      attributes: attributes ?? {},
    }
    await fetch(buildJournalClientEventUrl(resolveJournalApiBase()), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    })
  } catch {
    // Recovery must not depend on journal delivery.
  }
}
