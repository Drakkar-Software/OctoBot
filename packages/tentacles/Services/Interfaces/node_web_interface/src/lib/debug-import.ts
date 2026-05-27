import type {
  AutomationState,
  Debug,
  DebugState,
  UserAction,
} from "@/client"
import { resolveOneOfInstance } from "@/lib/debug-protocol-oneof"

export type ParseDebugStateJsonResult =
  | { state: DebugState }
  | { error: string }

export type ImportedDebugSummary = {
  version: string
  importedAt: Date
  sourceLabel: string
  latestStateUpdatedAt: string | null
  counts: {
    automations: number
    userActions: number
    accounts: number
    exchangeConfigs: number
    strategies: number
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function readOptionalString(
  object: Record<string, unknown>,
  key: string,
): string | null {
  if (!(key in object)) return null
  const value = object[key]
  if (value == null || value === "") return null
  return String(value)
}

function parseTimestampMs(value: string | null | undefined): number | null {
  if (!value) return null
  const time = new Date(value).getTime()
  return Number.isNaN(time) ? null : time
}

function collectTimestamp(
  timestamps: Array<{ ms: number; iso: string }>,
  value: string | null | undefined,
): void {
  if (!value) return
  const ms = parseTimestampMs(value)
  if (ms === null) return
  timestamps.push({ ms, iso: value })
}

function readUserActionResultUpdatedAt(
  result: UserAction["result"],
): string | null {
  const instance = resolveOneOfInstance<{ updated_at?: string | null }>(result)
  if (!instance?.updated_at) return null
  return String(instance.updated_at)
}

function collectAutomationTimestamps(
  automation: AutomationState,
  timestamps: Array<{ ms: number; iso: string }>,
): void {
  collectTimestamp(timestamps, automation.metadata.updated_at)
  const actions = automation.actions ?? []
  for (const action of actions) {
    collectTimestamp(timestamps, action.completed_at)
  }
}

function collectUserActionTimestamps(
  userAction: UserAction,
  timestamps: Array<{ ms: number; iso: string }>,
): void {
  collectTimestamp(timestamps, userAction.updated_at)
  collectTimestamp(timestamps, readUserActionResultUpdatedAt(userAction.result))
}

function normalizeDebugLists(debug: Debug): Debug {
  return {
    ...debug,
    automations: debug.automations ?? [],
    user_actions: debug.user_actions ?? [],
    accounts: debug.accounts ?? [],
    exchange_configs: debug.exchange_configs ?? [],
    account_tradings: debug.account_tradings ?? [],
    local_strategies: debug.local_strategies ?? [],
  }
}

export function parseDebugStateJson(text: string): ParseDebugStateJsonResult {
  const trimmed = text.trim()
  if (!trimmed) {
    return { error: "JSON cannot be empty" }
  }

  let parsed: unknown
  try {
    parsed = JSON.parse(trimmed) as unknown
  } catch (error) {
    const message = error instanceof Error ? error.message : "Invalid JSON"
    return { error: message }
  }

  if (!isRecord(parsed)) {
    return { error: "Request body must be a JSON object" }
  }

  const version = readOptionalString(parsed, "version")
  if (!version) {
    return { error: 'Payload must include a string "version" field' }
  }

  if (!("debug" in parsed) || !isRecord(parsed.debug)) {
    return { error: 'Payload must include a "debug" object' }
  }

  const debugRecord = parsed.debug
  if (!Array.isArray(debugRecord.automations)) {
    return { error: 'debug.automations must be an array' }
  }
  if (!Array.isArray(debugRecord.user_actions)) {
    return { error: 'debug.user_actions must be an array' }
  }

  const debug = normalizeDebugLists(parsed.debug as Debug)

  return {
    state: {
      version,
      debug,
    },
  }
}

export function getDebugStateLatestUpdatedAt(
  state: DebugState,
): string | null {
  const debug = state.debug
  if (!debug) return null

  const timestamps: Array<{ ms: number; iso: string }> = []

  for (const automation of debug.automations ?? []) {
    collectAutomationTimestamps(automation, timestamps)
  }
  for (const userAction of debug.user_actions ?? []) {
    collectUserActionTimestamps(userAction, timestamps)
  }
  for (const account of debug.accounts ?? []) {
    collectTimestamp(timestamps, account.updated_at)
  }
  for (const tradingSummary of debug.account_tradings ?? []) {
    collectTimestamp(timestamps, tradingSummary.account_trading?.updated_at)
  }
  for (const strategy of debug.local_strategies ?? []) {
    collectTimestamp(timestamps, strategy.updated_at)
  }

  if (!timestamps.length) return null

  let latest = timestamps[0]
  for (const entry of timestamps.slice(1)) {
    if (entry.ms >= latest.ms) {
      latest = entry
    }
  }
  return latest.iso
}

export function summarizeImportedDebugState(
  state: DebugState,
  meta: { importedAt: Date; sourceLabel: string },
): ImportedDebugSummary {
  const debug = state.debug
  return {
    version: state.version,
    importedAt: meta.importedAt,
    sourceLabel: meta.sourceLabel,
    latestStateUpdatedAt: getDebugStateLatestUpdatedAt(state),
    counts: {
      automations: debug?.automations?.length ?? 0,
      userActions: debug?.user_actions?.length ?? 0,
      accounts: debug?.accounts?.length ?? 0,
      exchangeConfigs: debug?.exchange_configs?.length ?? 0,
      strategies: debug?.local_strategies?.length ?? 0,
    },
  }
}

export function sanitizeDebugExportFilename(filename: string): string {
  const withoutExtension = filename.replace(/\.json$/i, "")
  const sanitized = withoutExtension.replace(/[^a-z0-9\-_]/gi, "_").substring(0, 200)
  return sanitized.length > 0 ? `${sanitized}.json` : "debug-state.json"
}

export function buildDebugExportFilename(walletAddress: string): string {
  const stamp = new Date()
    .toISOString()
    .replace(/[-:]/g, "")
    .replace(/\..+/, "")
    .slice(0, 13)
  const normalized = walletAddress.trim().toLowerCase()
  const walletSuffix =
    normalized.length >= 8 ? normalized.slice(-8) : normalized || "current"
  return sanitizeDebugExportFilename(`debug-state-${stamp}-${walletSuffix}`)
}

export function downloadDebugStateJson(
  state: DebugState,
  filename: string,
): void {
  const json = JSON.stringify(state, null, 2)
  const blob = new Blob([json], { type: "application/json;charset=utf-8;" })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = sanitizeDebugExportFilename(filename)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
