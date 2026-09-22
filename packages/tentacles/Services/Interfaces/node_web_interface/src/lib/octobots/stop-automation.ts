import type { TaskOutput as Task, UserAction } from "@/client"
import { formatApiErrorDetailMessage } from "@/lib/api-error"
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
  return formatApiErrorDetailMessage(
    error,
    "Couldn't stop this OctoBot. Try again.",
  )
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
