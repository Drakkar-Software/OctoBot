import { formatApiErrorDetailMessage } from "@/lib/api-error"

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
  return formatApiErrorDetailMessage(
    error,
    "Couldn't create your OctoBot. Try again.",
  )
}
