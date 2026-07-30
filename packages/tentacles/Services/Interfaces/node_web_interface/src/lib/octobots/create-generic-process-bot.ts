import type { ApiError } from "@/client"

export type CreateGenericProcessBotNameValidation =
  | { valid: true; trimmedName: string }
  | { valid: false; message: string }

export function validateCreateGenericProcessBotName(
  name: string,
): CreateGenericProcessBotNameValidation {
  const trimmedName = name.trim()
  if (trimmedName.length === 0) {
    return { valid: false, message: "Enter a name for your OctoBot." }
  }
  return { valid: true, trimmedName }
}

export function buildCreateGenericProcessBotRequestBody(trimmedName: string) {
  return { name: trimmedName }
}

export function formatCreateGenericProcessBotError(error: unknown): string {
  if (error instanceof Error && error.name === "ApiError") {
    const apiError = error as ApiError
    const detail = (apiError.body as { detail?: unknown } | undefined)?.detail
    if (typeof detail === "string" && detail.trim().length > 0) {
      return detail
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string }
      if (typeof first?.msg === "string" && first.msg.trim().length > 0) {
        return first.msg
      }
    }
    if (apiError.message.trim().length > 0) {
      return apiError.message
    }
  }
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message
  }
  return "Couldn't create your OctoBot. Try again."
}
