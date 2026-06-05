import type { UserAction } from "@/client"
import { resolveOneOfInstance } from "@/lib/debug/protocol-oneof"

export function getConfigurationActionType(
  configuration: UserAction["configuration"],
): string {
  const instance = resolveOneOfInstance<{ action_type?: string }>(configuration)
  if (!instance?.action_type) return "—"
  return String(instance.action_type)
}

export function getUserActionResultField(
  result: UserAction["result"],
  field: "error_message" | "error_details",
): string {
  const instance = resolveOneOfInstance<Record<string, unknown>>(result)
  if (!instance) return "—"
  const value = instance[field]
  if (value == null || value === "") return "—"
  return String(value)
}

export function getUserActionResultErrorMessage(
  result: UserAction["result"],
): string {
  return getUserActionResultField(result, "error_message")
}

export function getUserActionResultErrorDetails(
  result: UserAction["result"],
): string {
  return getUserActionResultField(result, "error_details")
}

export function getUserActionUpdatedAt(
  userAction: UserAction,
): string | null | undefined {
  const instance = resolveOneOfInstance<{ updated_at?: string | null }>(
    userAction.result,
  )
  if (instance?.updated_at) return String(instance.updated_at)
  if (userAction.updated_at) return userAction.updated_at
  return userAction.created_at ?? undefined
}

export function validateUserActionJson(text: string): string | null {
  const trimmed = text.trim()
  if (!trimmed) return "JSON cannot be empty"
  try {
    const parsed = JSON.parse(trimmed) as UserAction
    if (!parsed.id || typeof parsed.id !== "string") {
      return 'Payload must include a string "id" field'
    }
    return null
  } catch (error) {
    return error instanceof Error ? error.message : "Invalid JSON"
  }
}
