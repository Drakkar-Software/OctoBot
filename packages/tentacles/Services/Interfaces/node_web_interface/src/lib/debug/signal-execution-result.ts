import type {
  AutomationActionResult,
  SignalPriorityActionExecutionResult,
  UserAction,
} from "@/client"
import { getDebugStatusDisplay } from "@/lib/debug/display-utils"
import { resolveOneOfInstance } from "@/lib/debug/protocol-oneof"

export function isSuccessfulSignalPriorityActionResult(
  item: SignalPriorityActionExecutionResult,
): boolean {
  const errorStatus = item.error_status
  if (errorStatus == null || errorStatus === "") {
    return true
  }
  return errorStatus === "no_error"
}

export function getAutomationActionResult(
  result: UserAction["result"],
): AutomationActionResult | null {
  return resolveOneOfInstance<AutomationActionResult>(result)
}

export function getSignalExecutionResults(
  result: UserAction["result"],
): SignalPriorityActionExecutionResult[] {
  const automationResult = getAutomationActionResult(result)
  return automationResult?.signal_execution_results ?? []
}

export function formatSignalExecutionResultsSummary(
  results: SignalPriorityActionExecutionResult[],
): string {
  if (results.length === 0) {
    return "—"
  }
  let okCount = 0
  let failedCount = 0
  for (const item of results) {
    if (isSuccessfulSignalPriorityActionResult(item)) {
      okCount += 1
    } else {
      failedCount += 1
    }
  }
  if (failedCount === 0) {
    return `${okCount} OK`
  }
  if (okCount === 0) {
    return `${failedCount} failed`
  }
  return `${okCount} OK · ${failedCount} failed`
}

export function formatSignalExecutionResultTooltipLines(
  results: SignalPriorityActionExecutionResult[],
): string[] {
  return results.map((item) => {
    const actionId = item.priority_action_id
    if (isSuccessfulSignalPriorityActionResult(item)) {
      const { emoji } = getDebugStatusDisplay("completed")
      return `${emoji} ${actionId} — OK`
    }
    const errorStatus = item.error_status ?? "failed"
    const { emoji } = getDebugStatusDisplay(errorStatus)
    const errorMessage = item.error_message?.trim()
    if (errorMessage) {
      return `${emoji} ${actionId} — ${errorStatus} — ${errorMessage}`
    }
    return `${emoji} ${actionId} — ${errorStatus}`
  })
}
