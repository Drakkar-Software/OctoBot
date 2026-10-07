import type { ApiError } from "@/client"

export type ParsedRateLimitDetail = {
  message: string
  unblockAt: number
}

function readDetailRecord(error: ApiError): Record<string, unknown> | null {
  const detail = (error.body as { detail?: unknown })?.detail
  if (detail === null || detail === undefined || typeof detail !== "object") {
    return null
  }
  return detail as Record<string, unknown>
}

export function parseRateLimitDetail(
  error: ApiError,
): ParsedRateLimitDetail | null {
  const detail = readDetailRecord(error)
  if (detail === null) {
    return null
  }
  const rawMessage = detail.message
  if (typeof rawMessage !== "string" || rawMessage.length === 0) {
    return null
  }
  const rawUnblockAt = detail.unblock_at
  if (typeof rawUnblockAt !== "number" || !Number.isFinite(rawUnblockAt)) {
    return null
  }
  return { message: rawMessage, unblockAt: rawUnblockAt }
}

export function formatRateLimitUnblockLocalTime(
  unblockAt: number,
  locale = "en-US",
): string {
  const formatted = new Intl.DateTimeFormat(locale, {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(unblockAt * 1000))
  return `Try again after ${formatted}.`
}
