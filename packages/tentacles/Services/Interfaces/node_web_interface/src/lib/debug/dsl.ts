import type { Action, AutomationState } from "@/client"
import { COMPOUND_DSL_KEYWORDS } from "@/lib/debug/constants"
import {
  getLatestExecutedAction,
  getNextPendingAction,
  getRunningAction,
  isRunningAutomation,
} from "@/lib/debug/automation"

export function extractFirstDslArgument(dsl: string): string | null {
  const openIndex = dsl.indexOf("(")
  if (openIndex === -1) return null
  let depth = 0
  const start = openIndex + 1
  for (let index = start; index < dsl.length; index++) {
    const char = dsl[index]
    if (char === "(") depth++
    else if (char === ")") {
      if (depth === 0) return dsl.slice(start, index).trim()
      depth--
    } else if (char === "," && depth === 0) {
      return dsl.slice(start, index).trim()
    }
  }
  return null
}

export function extractDslKeywordFromFragment(fragment: string): string | null {
  const match = fragment.trim().match(/^([a-zA-Z_][a-zA-Z0-9_]*)/)
  return match?.[1] ?? null
}

export function isCompoundDslKeyword(keyword: string): boolean {
  return COMPOUND_DSL_KEYWORDS.has(keyword)
}

export function buildCompoundDslSummary(dsl: string, keyword: string): string {
  const firstArgument = extractFirstDslArgument(dsl)
  if (!firstArgument) return keyword
  const nextKeyword = extractDslKeywordFromFragment(firstArgument)
  if (!nextKeyword) return keyword
  if (isCompoundDslKeyword(nextKeyword)) {
    return `${keyword}.${buildCompoundDslSummary(firstArgument, nextKeyword)}`
  }
  return `${keyword}.${nextKeyword}`
}

export function formatDslSummary(dsl: string | null | undefined): string {
  if (!dsl?.trim()) return "—"
  const trimmed = dsl.trim()
  const firstKeyword = extractDslKeywordFromFragment(trimmed)
  if (!firstKeyword) return "—"
  if (!isCompoundDslKeyword(firstKeyword)) {
    return firstKeyword
  }
  return buildCompoundDslSummary(trimmed, firstKeyword)
}

export function getActionDslKeyword(action: Action | undefined): string {
  if (!action) return "—"
  if (action.dsl) return formatDslSummary(action.dsl)
  return action.action_type || "—"
}

export function getAutomationDslHint(automation: AutomationState): string {
  const actions = automation.actions ?? []
  if (isRunningAutomation(automation)) {
    return getActionDslKeyword(getNextPendingAction(actions))
  }
  const runningAction = getRunningAction(actions)
  if (runningAction) {
    return getActionDslKeyword(runningAction)
  }
  return getActionDslKeyword(getLatestExecutedAction(actions))
}
