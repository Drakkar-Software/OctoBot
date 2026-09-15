import { reportUiJournalEvent } from "@/lib/journal-client-event"

export function reportShellFatalError(error: Error): void {
  void reportUiJournalEvent("ui_fatal_render_error", {
    error_name: error.name,
    error_category: error.constructor.name,
    route_path: window.location.pathname,
  })
}

export function reportBootFailed(error: Error): void {
  void reportUiJournalEvent("ui_boot_failed", {
    error_name: error.name,
    error_category: error.constructor.name,
    route_path: window.location.pathname,
  })
}

export function reportAuthStateBroken(): void {
  void reportUiJournalEvent("ui_auth_state_broken", {
    has_username: Boolean(localStorage.getItem("auth_username")),
    has_password_record: false,
  })
}

export function reportInsecureContext(context: {
  isSecureContext: boolean
  hostname: string
}): void {
  void reportUiJournalEvent("ui_insecure_context", {
    is_secure_context: context.isSecureContext,
    hostname: context.hostname,
  })
}
