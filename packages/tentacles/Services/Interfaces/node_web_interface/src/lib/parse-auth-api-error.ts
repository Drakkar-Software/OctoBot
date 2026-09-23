import type { ApiAuthErrorCode } from "@/lib/auth-error-codes"
import { API_AUTH_ERROR_CODES } from "@/lib/auth-error-codes"
import { getApiErrorResponseBody, isApiError } from "@/lib/api-error"

const API_AUTH_CODE_SET = new Set<string>(Object.values(API_AUTH_ERROR_CODES))

function readCodeFromDetail(detail: unknown): string | null {
  if (!detail || typeof detail !== "object" || !("code" in detail)) {
    return null
  }
  const code = (detail as { code: unknown }).code
  return typeof code === "string" ? code : null
}

export function parseAuthErrorCodeFromBody(body: unknown): ApiAuthErrorCode | null {
  if (!body || typeof body !== "object") {
    return null
  }
  const record = body as { detail?: unknown }
  const code =
    readCodeFromDetail(record.detail) ??
    readCodeFromDetail(body)
  if (!code || !API_AUTH_CODE_SET.has(code)) {
    return null
  }
  return code as ApiAuthErrorCode
}

export function parseAuthErrorCodeFromApiError(
  error: unknown,
): ApiAuthErrorCode | null {
  if (!isApiError(error)) {
    return null
  }
  return parseAuthErrorCodeFromBody(getApiErrorResponseBody(error))
}
