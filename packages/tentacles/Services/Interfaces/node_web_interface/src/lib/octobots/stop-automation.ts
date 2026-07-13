import type { ApiError, Task_Output as Task, UserAction } from "@/client"
import { buildAutomationStopUserActionJson } from "@/lib/debug/user-action-templates"
import { resolveOneOfInstance } from "@/lib/debug/protocol-oneof"
import { getActiveExecution, getStatusGroup } from "@/utils/executions"

export function canStopOctoBot(task: Task): boolean {
  const activeExecution = getActiveExecution(task.executions)
  if (!activeExecution?.status) return false
  return getStatusGroup(activeExecution.status) === "active"
}

export function buildStopAutomationUserAction(
  automationId: string,
): UserAction {
  return JSON.parse(
    buildAutomationStopUserActionJson(automationId),
  ) as UserAction
}

export function formatStopAutomationError(error: unknown): string {
  if (error instanceof Error && error.name === "ApiError") {
    const apiError = error as ApiError
    const detail = (apiError.body as { detail?: unknown } | undefined)?.detail
    if (typeof detail === "string" && detail.trim().length > 0) {
      return detail
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const firstDetail = detail[0] as { msg?: string }
      if (
        typeof firstDetail?.msg === "string" &&
        firstDetail.msg.trim().length > 0
      ) {
        return firstDetail.msg
      }
    }
    if (apiError.message.trim().length > 0) {
      return apiError.message
    }
  }
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message
  }
  return "Couldn't stop this OctoBot. Try again."
}

export function getStopAutomationConfigurationActionType(
  userAction: UserAction,
): string | undefined {
  const configuration = resolveOneOfInstance<{ action_type?: string }>(
    userAction.configuration,
  )
  return configuration?.action_type
}

export function getStopAutomationTargetId(
  userAction: UserAction,
): string | undefined {
  const configuration = resolveOneOfInstance<{ id?: string }>(
    userAction.configuration,
  )
  return configuration?.id
}

export function getOctoBotDisplayName(task: Task): string {
  const activeExecution = getActiveExecution(task.executions)
  return (
    task.name ||
    activeExecution?.name ||
    `OctoBot ${task.id?.slice(0, 6) || "new"}`
  )
}
