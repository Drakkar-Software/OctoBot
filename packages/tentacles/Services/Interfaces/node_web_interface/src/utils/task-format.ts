export function formatDate(value: string | null | undefined): string {
  if (!value) return "—"
  try {
    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value))
  } catch {
    return value
  }
}

export function formatIsoTooltip(value: string): string {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
    return `${new Date(value).toISOString()} (${tz})`
  } catch {
    return value
  }
}

export function formatRelativeFuture(value: string): string {
  try {
    const diffMs = new Date(value).getTime() - Date.now()
    if (diffMs <= 0) return "Starting soon…"
    const secs = Math.floor(diffMs / 1000)
    if (secs < 60) return `in ${secs}s`
    const mins = Math.floor(secs / 60)
    if (mins < 60) return `in ${mins}m`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `in ${hours}h ${mins % 60}m`
    return formatDate(value)
  } catch {
    return formatDate(value)
  }
}

export function formatElapsed(value: string): string {
  try {
    const secs = Math.floor((Date.now() - new Date(value).getTime()) / 1000)
    if (secs < 60) return `${secs}s`
    const mins = Math.floor(secs / 60)
    if (mins < 60) return `${mins}m ${secs % 60}s`
    const hours = Math.floor(mins / 60)
    return `${hours}h ${mins % 60}m`
  } catch {
    return ""
  }
}

export function parseActionCount(
  actions: string | null | undefined,
): number | null {
  if (!actions) return null
  try {
    const parsed = JSON.parse(actions)
    return Array.isArray(parsed) ? parsed.length : null
  } catch {
    return null
  }
}
