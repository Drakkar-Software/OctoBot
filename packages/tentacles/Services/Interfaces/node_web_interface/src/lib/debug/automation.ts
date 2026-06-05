import type { Action, AutomationSignalType, AutomationState } from "@/client"
import { parseSortTime } from "@/lib/table"

export function signalTypeRequiresPayload(
  signalType: AutomationSignalType,
): boolean {
  return signalType === "actions" || signalType === "trading_signal"
}

export function isRunningAutomation(automation: AutomationState): boolean {
  return automation.status === "running"
}

export function getAutomationErrorTooltipLines(
  automation: AutomationState,
): string[] {
  const lines: string[] = []
  if (automation.error) {
    lines.push(`error: ${automation.error}`)
  }
  if (automation.error_message) {
    lines.push(`error_message: ${automation.error_message}`)
  }
  return lines
}

export function getAutomationActions(automation: AutomationState): Action[] {
  return automation.actions ?? []
}

export function isActionExecuted(action: Action): boolean {
  return action.completed_at != null || action.status === "completed"
}

export function getActionExecutionStats(automation: AutomationState): {
  executed: number
  total: number
} {
  const actions = getAutomationActions(automation)
  return {
    total: actions.length,
    executed: actions.filter(isActionExecuted).length,
  }
}

export function getLatestExecutedAction(actions: Action[]): Action | undefined {
  let latest: Action | undefined
  let latestTime = Number.NEGATIVE_INFINITY
  for (const action of actions) {
    if (!action.completed_at) continue
    const time = parseSortTime(action.completed_at)
    if (time >= latestTime) {
      latestTime = time
      latest = action
    }
  }
  return latest
}

export function getNextPendingAction(actions: Action[]): Action | undefined {
  return actions.find((action) => !action.completed_at)
}

export function getRunningAction(actions: Action[]): Action | undefined {
  return actions.find((action) => action.status === "running")
}

export function getAutomationUpdatedAt(
  automation: AutomationState,
): string | null | undefined {
  if (automation.metadata.updated_at) {
    return automation.metadata.updated_at
  }
  const actions = getAutomationActions(automation)
  let latest: string | null = null
  let latestTime = Number.NEGATIVE_INFINITY
  for (const action of actions) {
    if (!action.completed_at) continue
    const time = parseSortTime(action.completed_at)
    if (time >= latestTime) {
      latestTime = time
      latest = action.completed_at
    }
  }
  return latest
}

export function formatActionProgress(automation: AutomationState): string {
  const { executed, total } = getActionExecutionStats(automation)
  return `${executed}/${total}`
}

export function validateAutomationCanReceiveSignal(
  automation: AutomationState,
): string | null {
  if (!isRunningAutomation(automation)) {
    return "Only running automations can receive signals."
  }
  return null
}
