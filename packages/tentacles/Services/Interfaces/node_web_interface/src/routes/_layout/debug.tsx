import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  Bug,
  Copy,
  Download,
  Eye,
  FileText,
  Pencil,
  Play,
  RefreshCw,
  TriangleAlert,
  Upload,
  X,
  Zap,
} from "lucide-react"
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type ClipboardEvent,
  type ReactNode,
} from "react"
import { toast } from "sonner"

import {
  type Action,
  type Account,
  type AccountTradingWithAccountId,
  type ApiError,
  type AutomationSignalType,
  type AutomationState,
  type DebugState,
  DebugService,
  type ExchangeConfig,
  type Strategy,
  type UserAction,
  type UserActionType,
  WalletsService,
} from "@/client"
import { Button } from "@/components/ui/button"
import { CollapsibleJsonView } from "@/components/ui/collapsible-json-view"
import { LineNumberTextarea } from "@/components/ui/line-number-textarea"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { getDebugQueryOptions } from "@/lib/debug-queries"
import {
  buildDebugExportFilename,
  downloadDebugStateJson,
  type ImportedDebugSummary,
  parseDebugStateJson,
  summarizeImportedDebugState,
} from "@/lib/debug-import"
import {
  type AssetsListEntry,
  countAccountAssets,
  formatAssetsPortfolioTooltip,
  formatAssetsSymbolsSummary,
  formatDebugStatusTooltip,
  getAccountExchangeNames,
  getAccountOrdersCount,
  getAccountOrdersTooltipContent,
  getAccountTradesCount,
  getAccountTradesTooltipContent,
  getAutomationOrdersTooltipContent,
  getAutomationTradesTooltipContent,
  type DebugTableColumnAlign,
  debugTableCellClass,
  getDebugStatusDisplay,
  matchesColumnFilter,
  matchesDebugStatusColumnFilter,
  getAccountsReferencingExchangeConfig,
  getStrategyConfigurationType,
} from "@/lib/debug-display-utils"
import { resolveOneOfInstance } from "@/lib/debug-protocol-oneof"
import {
  buildAccountEditUserActionJson,
  buildAutomationCreateUserActionJsonForAccount,
  buildAutomationCreateUserActionJsonForStrategy,
  buildAutomationSignalUserActionJson,
  buildAutomationStopUserActionJson,
  buildExchangeConfigEditUserActionJson,
  buildStrategyEditUserActionJson,
  buildUserActionTemplateJson,
  DEFAULT_USER_ACTION_TEMPLATE_KEY,
  defaultSignalPayloadText,
  USER_ACTION_TEMPLATE_OPTIONS,
  type UserActionTemplateKey,
  userActionTemplateKeyFromActionType,
} from "@/lib/debug-user-action-templates"
import { truncateAddress } from "@/lib/wallet-utils"
import { cn } from "@/lib/utils"
import { handleError } from "@/utils"

const SIGNAL_TYPE_OPTIONS: {
  value: AutomationSignalType
  label: string
}[] = [
  { value: "forced_trigger", label: "Forced trigger" },
  { value: "actions", label: "Actions" },
  { value: "trading_signal", label: "Trading signal" },
]

function signalTypeRequiresPayload(
  signalType: AutomationSignalType,
): boolean {
  return signalType === "actions" || signalType === "trading_signal"
}

function isRunningAutomation(automation: AutomationState): boolean {
  return automation.status === "running"
}

function getAutomationErrorTooltipLines(automation: AutomationState): string[] {
  const lines: string[] = []
  if (automation.error) {
    lines.push(`error: ${automation.error}`)
  }
  if (automation.error_message) {
    lines.push(`error_message: ${automation.error_message}`)
  }
  return lines
}

function getAutomationActions(automation: AutomationState): Action[] {
  return automation.actions ?? []
}

function isActionExecuted(action: Action): boolean {
  return action.completed_at != null || action.status === "completed"
}

function getActionExecutionStats(automation: AutomationState): {
  executed: number
  total: number
} {
  const actions = getAutomationActions(automation)
  return {
    total: actions.length,
    executed: actions.filter(isActionExecuted).length,
  }
}

function extractFirstDslArgument(dsl: string): string | null {
  const openIndex = dsl.indexOf("(")
  if (openIndex === -1) return null
  let depth = 0
  const start = openIndex + 1
  for (let i = start; i < dsl.length; i++) {
    const char = dsl[i]
    if (char === "(") depth++
    else if (char === ")") {
      if (depth === 0) return dsl.slice(start, i).trim()
      depth--
    } else if (char === "," && depth === 0) {
      return dsl.slice(start, i).trim()
    }
  }
  return null
}

function extractDslKeywordFromFragment(fragment: string): string | null {
  const match = fragment.trim().match(/^([a-zA-Z_][a-zA-Z0-9_]*)/)
  return match?.[1] ?? null
}

const COMPOUND_DSL_KEYWORDS = new Set(["if_error", "loop_until", "value_if"])

function isCompoundDslKeyword(keyword: string): boolean {
  return COMPOUND_DSL_KEYWORDS.has(keyword)
}

function buildCompoundDslSummary(dsl: string, keyword: string): string {
  const firstArgument = extractFirstDslArgument(dsl)
  if (!firstArgument) return keyword
  const nextKeyword = extractDslKeywordFromFragment(firstArgument)
  if (!nextKeyword) return keyword
  if (isCompoundDslKeyword(nextKeyword)) {
    return `${keyword}.${buildCompoundDslSummary(firstArgument, nextKeyword)}`
  }
  return `${keyword}.${nextKeyword}`
}

function formatDslSummary(dsl: string | null | undefined): string {
  if (!dsl?.trim()) return "—"
  const trimmed = dsl.trim()
  const firstKeyword = extractDslKeywordFromFragment(trimmed)
  if (!firstKeyword) return "—"
  if (!isCompoundDslKeyword(firstKeyword)) {
    return firstKeyword
  }
  return buildCompoundDslSummary(trimmed, firstKeyword)
}

function getActionDslKeyword(action: Action | undefined): string {
  if (!action) return "—"
  if (action.dsl) return formatDslSummary(action.dsl)
  return action.action_type || "—"
}

const ID_DISPLAY_LENGTH = 8
const ERROR_DETAILS_DISPLAY_LENGTH = 35
const LATEST_ACTION_DISPLAY_LENGTH = 22
const AUTOMATION_NAME_DISPLAY_LENGTH = 20
const USER_ACTION_ID_DISPLAY_LENGTH = 32
/** Short tooltips (assets, status errors): no overflow so Radix collision sizing does not force a scrollbar. */
const COMPACT_TOOLTIP_CONTENT_CLASS =
  "font-mono text-xs text-left max-w-md whitespace-pre-line break-all p-3 [text-wrap:wrap]"

const SCROLLABLE_TOOLTIP_INNER_CLASS =
  "max-h-[min(90vh,var(--radix-tooltip-content-available-height,90vh))] overflow-y-auto overflow-x-hidden whitespace-pre-wrap break-all p-3 font-mono text-xs text-left [text-wrap:wrap]"

function ScrollableTooltipContent({
  children,
  side = "top",
  className,
}: {
  children: ReactNode
  side?: "top" | "right" | "bottom" | "left"
  className?: string
}) {
  return (
    <TooltipContent
      side={side}
      className={cn("max-w-3xl p-0 [text-wrap:wrap]", className)}
    >
      <div className={SCROLLABLE_TOOLTIP_INNER_CLASS}>{children}</div>
    </TooltipContent>
  )
}

function DebugStatusCell({
  status,
  extraTooltipLines,
  pulseWhenRunning = false,
}: {
  status: string | null | undefined
  extraTooltipLines?: string[]
  pulseWhenRunning?: boolean
}) {
  const { emoji, label } = getDebugStatusDisplay(status)
  const tooltip = formatDebugStatusTooltip(status, extraTooltipLines)
  const isLive = pulseWhenRunning && status?.toLowerCase() === "running"

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn(
            "cursor-default text-base leading-none",
            isLive && "animate-pulse",
          )}
          aria-label={label}
        >
          {emoji}
        </span>
      </TooltipTrigger>
      <TooltipContent side="top" className={COMPACT_TOOLTIP_CONTENT_CLASS}>
        {tooltip}
      </TooltipContent>
    </Tooltip>
  )
}

function formatIdDisplay(id: string): string {
  if (id.length <= ID_DISPLAY_LENGTH) return id
  return id.slice(0, ID_DISPLAY_LENGTH)
}

function TruncatedTextWithTooltip({
  text,
  maxLength = ERROR_DETAILS_DISPLAY_LENGTH,
  className,
}: {
  text: string
  maxLength?: number
  className?: string
}) {
  if (text === "—" || text.length <= maxLength) {
    return <span className={className}>{text}</span>
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className={`cursor-default ${className ?? ""}`}>
          {text.slice(0, maxLength)}…
        </span>
      </TooltipTrigger>
      <ScrollableTooltipContent>{text}</ScrollableTooltipContent>
    </Tooltip>
  )
}

function copyTextToClipboard(text: string, description: string): void {
  void navigator.clipboard.writeText(text).then(() => {
    toast.success("Copied to clipboard", { description })
  })
}

function CopyableIdCell({ id }: { id: string }) {
  const copy = () => {
    copyTextToClipboard(id, id)
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="font-mono text-xs cursor-pointer hover:text-foreground"
          aria-label={`Copy ID ${id}`}
          onClick={copy}
        >
          {formatIdDisplay(id)}
        </button>
      </TooltipTrigger>
      <TooltipContent side="top" className="font-mono text-xs max-w-md break-all p-3">
        {id}
      </TooltipContent>
    </Tooltip>
  )
}

function getLatestExecutedAction(actions: Action[]): Action | undefined {
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

function getNextPendingAction(actions: Action[]): Action | undefined {
  return actions.find((action) => !action.completed_at)
}

function getRunningAction(actions: Action[]): Action | undefined {
  return actions.find((action) => action.status === "running")
}

function getAutomationDslHint(automation: AutomationState): string {
  const actions = getAutomationActions(automation)
  if (isRunningAutomation(automation)) {
    return getActionDslKeyword(getNextPendingAction(actions))
  }
  const runningAction = getRunningAction(actions)
  if (runningAction) {
    return getActionDslKeyword(runningAction)
  }
  return getActionDslKeyword(getLatestExecutedAction(actions))
}

function getAutomationUpdatedAt(
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

function formatActionProgress(automation: AutomationState): string {
  const { executed, total } = getActionExecutionStats(automation)
  return `${executed}/${total}`
}

export const Route = createFileRoute("/_layout/debug")({
  component: DebugPage,
  head: () => ({
    meta: [{ title: "Debug view" }],
  }),
})

type SortDirection = "asc" | "desc"

type SortState<K extends string> = {
  key: K
  dir: SortDirection
}

const DEBUG_DATE_TIME_FORMATTER = new Intl.DateTimeFormat(undefined, {
  year: "2-digit",
  month: "numeric",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  second: "2-digit",
})

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—"
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : DEBUG_DATE_TIME_FORMATTER.format(d)
}

function debugColumnClass(
  align: DebugTableColumnAlign,
  extra?: string,
): string {
  return debugTableCellClass(align, extra)
}

function CenteredCellContent({ children }: { children: ReactNode }) {
  return <div className="flex justify-center">{children}</div>
}

const AUTOMATION_ASSETS_MAX_VISIBLE = 2

function AssetsPortfolioCell({
  assets,
  maxVisible = 3,
}: {
  assets: Array<AssetsListEntry> | null | undefined
  maxVisible?: number
}) {
  const summary = formatAssetsSymbolsSummary(assets, maxVisible)
  const tooltip = formatAssetsPortfolioTooltip(assets)

  if (!tooltip) {
    return summary
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="cursor-default font-mono text-xs">{summary}</span>
      </TooltipTrigger>
      <TooltipContent side="top" className={COMPACT_TOOLTIP_CONTENT_CLASS}>
        {tooltip}
      </TooltipContent>
    </Tooltip>
  )
}

function AutomationTradingCountCell({
  count,
  tooltip,
}: {
  count: number
  tooltip: string | null
}) {
  if (count <= 0) {
    return <>0</>
  }
  if (!tooltip) {
    return <>{count}</>
  }
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="cursor-default">{count}</span>
      </TooltipTrigger>
      <ScrollableTooltipContent>{tooltip}</ScrollableTooltipContent>
    </Tooltip>
  )
}

function parseSortTime(value: string | null | undefined): number {
  if (!value) return Number.NEGATIVE_INFINITY
  const t = new Date(value).getTime()
  return Number.isNaN(t) ? Number.NEGATIVE_INFINITY : t
}

function compareStrings(a: string, b: string, dir: SortDirection): number {
  const cmp = a.localeCompare(b, undefined, { sensitivity: "base" })
  return dir === "asc" ? cmp : -cmp
}

function compareNumbers(a: number, b: number, dir: SortDirection): number {
  return dir === "asc" ? a - b : b - a
}

function toggleSort<K extends string>(
  current: SortState<K>,
  key: K,
): SortState<K> {
  if (current.key === key) {
    return { key, dir: current.dir === "asc" ? "desc" : "asc" }
  }
  return { key, dir: "asc" }
}

type ColumnFilters<K extends string> = Partial<Record<K, string>>

function hasActiveFilters<K extends string>(filters: ColumnFilters<K>): boolean {
  return (Object.values(filters) as (string | undefined)[]).some((v) =>
    Boolean(v?.trim()),
  )
}

function getActiveFilterKeys<K extends string>(
  filters: ColumnFilters<K>,
): K[] {
  return (Object.keys(filters) as K[]).filter((key) =>
    Boolean(filters[key]?.trim()),
  )
}

function matchesTableColumnFilter(
  key: string,
  values: Record<string, string>,
  filter: string | undefined,
  rawStatus?: string | null,
): boolean {
  if (key === "status" || key === "stateStatus") {
    return matchesDebugStatusColumnFilter(rawStatus, filter)
  }
  return matchesColumnFilter(values[key] ?? "", filter)
}

function ColumnFilterInput({
  value,
  onChange,
  placeholder = "Filter…",
}: {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="mt-1.5 h-7 w-full min-w-0 rounded border border-rule bg-input px-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-frost"
    />
  )
}

function setColumnFilter<K extends string>(
  filters: ColumnFilters<K>,
  key: K,
  value: string,
): ColumnFilters<K> {
  if (!value.trim()) {
    const next = { ...filters }
    delete next[key]
    return next
  }
  return { ...filters, [key]: value }
}

function SortableTableHead<K extends string>({
  label,
  sortKey,
  sort,
  onSort,
  className,
}: {
  label: string
  sortKey: K
  sort: SortState<K>
  onSort: (key: K) => void
  className?: string
}) {
  const active = sort.key === sortKey
  const Icon = active
    ? sort.dir === "asc"
      ? ArrowUp
      : ArrowDown
    : ArrowUpDown
  return (
    <TableHead className={className}>
      <button
        type="button"
        className="inline-flex items-center gap-1 hover:text-foreground text-inherit -ml-1 px-1 rounded-sm"
        onClick={() => onSort(sortKey)}
      >
        {label}
        <Icon
          className={`size-3.5 shrink-0 ${active ? "text-foreground" : "text-muted-foreground/60"}`}
        />
      </button>
    </TableHead>
  )
}

type AutomationSortKey =
  | "id"
  | "status"
  | "name"
  | "progress"
  | "dsl"
  | "trades"
  | "exchanges"
  | "assets"
  | "orders"
  | "updated"

const AUTOMATION_COMPACT_COLUMN_CLASS = "w-0 px-2"
const AUTOMATION_COMPACT_COLUMNS = new Set<AutomationSortKey>([
  "progress",
  "orders",
  "trades",
])

function automationFilterHeadClass(key: AutomationSortKey): string {
  return AUTOMATION_COMPACT_COLUMNS.has(key)
    ? `align-top pb-2 pt-0 ${AUTOMATION_COMPACT_COLUMN_CLASS}`
    : "align-top pb-2 pt-0"
}

function automationFilterValues(row: AutomationState): Record<
  AutomationSortKey,
  string
> {
  return {
    id: row.id,
    status: String(row.status),
    name: row.metadata.name,
    progress: formatActionProgress(row),
    dsl: getAutomationDslHint(row),
    trades: String(row.trades?.length ?? 0),
    exchanges: row.exchanges?.length ? row.exchanges.join(", ") : "—",
    assets: formatAssetsSymbolsSummary(
      row.assets,
      AUTOMATION_ASSETS_MAX_VISIBLE,
    ),
    orders: String(row.orders?.length ?? 0),
    updated: formatDateTime(getAutomationUpdatedAt(row)),
  }
}

function filterAutomations(
  rows: AutomationState[],
  filters: ColumnFilters<AutomationSortKey>,
): AutomationState[] {
  if (!hasActiveFilters(filters)) return rows
  const activeKeys = getActiveFilterKeys(filters)
  return rows.filter((row) => {
    const values = automationFilterValues(row)
    return activeKeys.every((key) =>
      matchesTableColumnFilter(key, values, filters[key], row.status),
    )
  })
}

function sortAutomations(
  rows: AutomationState[],
  sort: SortState<AutomationSortKey>,
): AutomationState[] {
  const { key, dir } = sort
  return [...rows].sort((a, b) => {
    switch (key) {
      case "id":
        return compareStrings(a.id, b.id, dir)
      case "status":
        return compareStrings(String(a.status), String(b.status), dir)
      case "name":
        return compareStrings(a.metadata.name, b.metadata.name, dir)
      case "progress": {
        const aStats = getActionExecutionStats(a)
        const bStats = getActionExecutionStats(b)
        const cmp = compareNumbers(aStats.executed, bStats.executed, dir)
        if (cmp !== 0) return cmp
        return compareNumbers(aStats.total, bStats.total, dir)
      }
      case "dsl":
        return compareStrings(getAutomationDslHint(a), getAutomationDslHint(b), dir)
      case "trades":
        return compareNumbers(
          a.trades?.length ?? 0,
          b.trades?.length ?? 0,
          dir,
        )
      case "exchanges":
        return compareNumbers(
          a.exchanges?.length ?? 0,
          b.exchanges?.length ?? 0,
          dir,
        )
      case "assets":
        return compareNumbers(
          countAccountAssets(a.assets),
          countAccountAssets(b.assets),
          dir,
        )
      case "orders":
        return compareNumbers(
          a.orders?.length ?? 0,
          b.orders?.length ?? 0,
          dir,
        )
      case "updated":
        return compareNumbers(
          parseSortTime(getAutomationUpdatedAt(a)),
          parseSortTime(getAutomationUpdatedAt(b)),
          dir,
        )
      default:
        return 0
    }
  })
}

type UserActionSortKey =
  | "id"
  | "status"
  | "actionType"
  | "updated"
  | "errorMessage"
  | "errorDetails"

function userActionFilterValues(row: UserAction): Record<
  UserActionSortKey,
  string
> {
  return {
    id: row.id,
    status: row.status ?? "—",
    actionType: getConfigurationActionType(row.configuration),
    updated: formatDateTime(getUserActionUpdatedAt(row)),
    errorMessage: getUserActionResultErrorMessage(row.result),
    errorDetails: getUserActionResultErrorDetails(row.result),
  }
}

function filterUserActions(
  rows: UserAction[],
  filters: ColumnFilters<UserActionSortKey>,
): UserAction[] {
  if (!hasActiveFilters(filters)) return rows
  const activeKeys = getActiveFilterKeys(filters)
  return rows.filter((row) => {
    const values = userActionFilterValues(row)
    return activeKeys.every((key) =>
      matchesTableColumnFilter(key, values, filters[key], row.status),
    )
  })
}

function sortUserActions(
  rows: UserAction[],
  sort: SortState<UserActionSortKey>,
): UserAction[] {
  const { key, dir } = sort
  return [...rows].sort((a, b) => {
    switch (key) {
      case "id":
        return compareStrings(a.id, b.id, dir)
      case "status":
        return compareStrings(a.status ?? "", b.status ?? "", dir)
      case "actionType":
        return compareStrings(
          getConfigurationActionType(a.configuration),
          getConfigurationActionType(b.configuration),
          dir,
        )
      case "updated":
        return compareNumbers(
          parseSortTime(getUserActionUpdatedAt(a)),
          parseSortTime(getUserActionUpdatedAt(b)),
          dir,
        )
      case "errorMessage":
        return compareStrings(
          getUserActionResultErrorMessage(a.result),
          getUserActionResultErrorMessage(b.result),
          dir,
        )
      case "errorDetails":
        return compareStrings(
          getUserActionResultErrorDetails(a.result),
          getUserActionResultErrorDetails(b.result),
          dir,
        )
      default:
        return 0
    }
  })
}

type AccountSortKey =
  | "id"
  | "authenticationId"
  | "name"
  | "updated"
  | "stateStatus"
  | "stateMessage"
  | "assets"
  | "orders"
  | "trades"
  | "simulated"
  | "exchange"

const ACCOUNT_COMPACT_COLUMN_CLASS = "w-0 px-2"
const ACCOUNT_COMPACT_COLUMNS = new Set<AccountSortKey>(["orders", "trades"])

function accountFilterHeadClass(key: AccountSortKey): string {
  return ACCOUNT_COMPACT_COLUMNS.has(key)
    ? `align-top pb-2 pt-0 ${ACCOUNT_COMPACT_COLUMN_CLASS}`
    : "align-top pb-2 pt-0"
}

function accountFilterValues(
  row: Account,
  exchangeConfigs: ExchangeConfig[],
  accountTradings: AccountTradingWithAccountId[],
): Record<AccountSortKey, string> {
  return {
    id: row.id,
    authenticationId: row.authentication_id ?? "—",
    name: row.name,
    updated: formatDateTime(row.updated_at),
    stateStatus: row.state?.status ?? "—",
    stateMessage: row.state?.message ?? "—",
    assets: formatAssetsSymbolsSummary(row.assets),
    orders: String(getAccountOrdersCount(row.id, accountTradings)),
    trades: String(getAccountTradesCount(row.id, accountTradings)),
    simulated: row.is_simulated ? "yes" : "no",
    exchange: getAccountExchangeNames(row, exchangeConfigs),
  }
}

function filterAccounts(
  rows: Account[],
  filters: ColumnFilters<AccountSortKey>,
  exchangeConfigs: ExchangeConfig[],
  accountTradings: AccountTradingWithAccountId[],
): Account[] {
  if (!hasActiveFilters(filters)) return rows
  const activeKeys = getActiveFilterKeys(filters)
  return rows.filter((row) => {
    const values = accountFilterValues(row, exchangeConfigs, accountTradings)
    return activeKeys.every((key) =>
      matchesTableColumnFilter(
        key,
        values,
        filters[key],
        row.state?.status,
      ),
    )
  })
}

function sortAccounts(
  rows: Account[],
  sort: SortState<AccountSortKey>,
  exchangeConfigs: ExchangeConfig[],
  accountTradings: AccountTradingWithAccountId[],
): Account[] {
  const { key, dir } = sort
  return [...rows].sort((a, b) => {
    switch (key) {
      case "id":
        return compareStrings(a.id, b.id, dir)
      case "authenticationId":
        return compareStrings(
          a.authentication_id ?? "",
          b.authentication_id ?? "",
          dir,
        )
      case "name":
        return compareStrings(a.name, b.name, dir)
      case "updated":
        return compareNumbers(
          parseSortTime(a.updated_at),
          parseSortTime(b.updated_at),
          dir,
        )
      case "stateStatus":
        return compareStrings(a.state?.status ?? "", b.state?.status ?? "", dir)
      case "stateMessage":
        return compareStrings(a.state?.message ?? "", b.state?.message ?? "", dir)
      case "assets":
        return compareNumbers(
          countAccountAssets(a.assets),
          countAccountAssets(b.assets),
          dir,
        )
      case "orders":
        return compareNumbers(
          getAccountOrdersCount(a.id, accountTradings),
          getAccountOrdersCount(b.id, accountTradings),
          dir,
        )
      case "trades":
        return compareNumbers(
          getAccountTradesCount(a.id, accountTradings),
          getAccountTradesCount(b.id, accountTradings),
          dir,
        )
      case "simulated":
        return compareNumbers(
          a.is_simulated ? 1 : 0,
          b.is_simulated ? 1 : 0,
          dir,
        )
      case "exchange":
        return compareStrings(
          getAccountExchangeNames(a, exchangeConfigs),
          getAccountExchangeNames(b, exchangeConfigs),
          dir,
        )
      default:
        return 0
    }
  })
}

type ExchangeConfigSortKey =
  | "id"
  | "exchange"
  | "name"
  | "accounts"
  | "sandboxed"
  | "url"

function exchangeConfigFilterValues(
  row: ExchangeConfig,
  accounts: Account[],
): Record<ExchangeConfigSortKey, string> {
  return {
    id: row.id,
    exchange: row.exchange,
    name: row.name,
    accounts: getAccountsReferencingExchangeConfig(row.id, accounts),
    sandboxed: row.sandboxed ? "yes" : "no",
    url: row.url ?? "—",
  }
}

function filterExchangeConfigs(
  rows: ExchangeConfig[],
  filters: ColumnFilters<ExchangeConfigSortKey>,
  accounts: Account[],
): ExchangeConfig[] {
  if (!hasActiveFilters(filters)) return rows
  return rows.filter((row) => {
    const values = exchangeConfigFilterValues(row, accounts)
    return (Object.keys(filters) as ExchangeConfigSortKey[]).every((key) =>
      matchesColumnFilter(values[key], filters[key]),
    )
  })
}

function sortExchangeConfigs(
  rows: ExchangeConfig[],
  sort: SortState<ExchangeConfigSortKey>,
  accounts: Account[],
): ExchangeConfig[] {
  const { key, dir } = sort
  return [...rows].sort((a, b) => {
    switch (key) {
      case "id":
        return compareStrings(a.id, b.id, dir)
      case "exchange":
        return compareStrings(a.exchange, b.exchange, dir)
      case "name":
        return compareStrings(a.name, b.name, dir)
      case "accounts":
        return compareStrings(
          getAccountsReferencingExchangeConfig(a.id, accounts),
          getAccountsReferencingExchangeConfig(b.id, accounts),
          dir,
        )
      case "sandboxed":
        return compareNumbers(
          a.sandboxed ? 1 : 0,
          b.sandboxed ? 1 : 0,
          dir,
        )
      case "url":
        return compareStrings(a.url ?? "", b.url ?? "", dir)
      default:
        return 0
    }
  })
}

type StrategySortKey =
  | "id"
  | "name"
  | "version"
  | "updated"
  | "description"
  | "referenceMarket"
  | "configType"

function strategyFilterValues(row: Strategy): Record<StrategySortKey, string> {
  return {
    id: row.id,
    name: row.name ?? "—",
    version: row.version,
    updated: formatDateTime(row.updated_at),
    description: row.description ?? "—",
    referenceMarket: row.reference_market,
    configType: getStrategyConfigurationType(row),
  }
}

function filterStrategies(
  rows: Strategy[],
  filters: ColumnFilters<StrategySortKey>,
): Strategy[] {
  if (!hasActiveFilters(filters)) return rows
  return rows.filter((row) => {
    const values = strategyFilterValues(row)
    return (Object.keys(filters) as StrategySortKey[]).every((key) =>
      matchesColumnFilter(values[key], filters[key]),
    )
  })
}

function compareStrategiesByIdThenUpdated(a: Strategy, b: Strategy): number {
  const idCmp = compareStrings(a.id, b.id, "asc")
  if (idCmp !== 0) return idCmp
  return compareNumbers(
    parseSortTime(a.updated_at),
    parseSortTime(b.updated_at),
    "desc",
  )
}

function sortStrategies(
  rows: Strategy[],
  sort: SortState<StrategySortKey>,
): Strategy[] {
  const { key, dir } = sort
  return [...rows].sort((a, b) => {
    let cmp = 0
    switch (key) {
      case "id":
        cmp = compareStrings(a.id, b.id, dir)
        break
      case "name":
        cmp = compareStrings(a.name ?? "", b.name ?? "", dir)
        break
      case "version":
        cmp = compareStrings(a.version, b.version, dir)
        break
      case "updated":
        cmp = compareNumbers(
          parseSortTime(a.updated_at),
          parseSortTime(b.updated_at),
          dir,
        )
        break
      case "description":
        cmp = compareStrings(a.description ?? "", b.description ?? "", dir)
        break
      case "referenceMarket":
        cmp = compareStrings(a.reference_market, b.reference_market, dir)
        break
      case "configType":
        cmp = compareStrings(
          getStrategyConfigurationType(a),
          getStrategyConfigurationType(b),
          dir,
        )
        break
      default:
        cmp = 0
    }
    if (cmp !== 0) return cmp
    return compareStrategiesByIdThenUpdated(a, b)
  })
}

function getConfigurationActionType(
  configuration: UserAction["configuration"],
): string {
  const instance = resolveOneOfInstance<{ action_type?: string }>(configuration)
  if (!instance?.action_type) return "—"
  return String(instance.action_type)
}

function getUserActionResultField(
  result: UserAction["result"],
  field: "error_message" | "error_details",
): string {
  const instance = resolveOneOfInstance<Record<string, unknown>>(result)
  if (!instance) return "—"
  const value = instance[field]
  if (value == null || value === "") return "—"
  return String(value)
}

function getUserActionResultErrorMessage(
  result: UserAction["result"],
): string {
  return getUserActionResultField(result, "error_message")
}

function getUserActionResultErrorDetails(
  result: UserAction["result"],
): string {
  return getUserActionResultField(result, "error_details")
}

function getUserActionUpdatedAt(
  userAction: UserAction,
): string | null | undefined {
  const instance = resolveOneOfInstance<{ updated_at?: string | null }>(
    userAction.result,
  )
  if (instance?.updated_at) return String(instance.updated_at)
  if (userAction.updated_at) return userAction.updated_at
  return userAction.created_at ?? undefined
}

function JsonDetailDialog({
  title,
  data,
  open,
  onOpenChange,
}: {
  title: string
  data: unknown
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>Full JSON payload</DialogDescription>
        </DialogHeader>
        {data != null ? (
          <CollapsibleJsonView value={data} />
        ) : (
          <p className="text-sm text-muted-foreground">—</p>
        )}
      </DialogContent>
    </Dialog>
  )
}

function SignalAutomationDialog({
  automation,
  open,
  onOpenChange,
  walletAddress,
  onSuccess,
}: {
  automation: AutomationState | null
  open: boolean
  onOpenChange: (open: boolean) => void
  walletAddress?: string
  onSuccess: () => void
}) {
  const [signalType, setSignalType] =
    useState<AutomationSignalType>("forced_trigger")
  const [payloadText, setPayloadText] = useState("")
  const [parseError, setParseError] = useState<string | null>(null)
  const { showSuccessToast, showErrorToast } = useCustomToast()

  useEffect(() => {
    if (open) {
      setSignalType("forced_trigger")
      setPayloadText("")
      setParseError(null)
    }
  }, [open, automation?.id])

  const mutation = useMutation({
    mutationFn: (body: UserAction) =>
      DebugService.executeUserAction({
        requestBody: body,
        walletAddress: walletAddress ?? null,
      }),
    onSuccess: () => {
      showSuccessToast("Signal submitted")
      onOpenChange(false)
      onSuccess()
    },
    onError: (error) => {
      handleError.bind(showErrorToast)(error as ApiError)
    },
  })

  const handleSignalTypeChange = (value: AutomationSignalType) => {
    setSignalType(value)
    setParseError(null)
    if (signalTypeRequiresPayload(value)) {
      setPayloadText(defaultSignalPayloadText(value))
    }
  }

  const handleSend = () => {
    if (!automation) return
    if (!isRunningAutomation(automation)) {
      setParseError("Only running automations can receive signals.")
      return
    }
    const configuration: UserAction["configuration"] = {
      action_type: "automation_signal",
      automation_id: automation.id,
      signal_type: signalType,
    } as UserAction["configuration"]

    if (signalTypeRequiresPayload(signalType)) {
      try {
        const parsed = JSON.parse(payloadText) as unknown
        setParseError(null)
        ;(configuration as Record<string, unknown>).signal_payload = parsed
      } catch (e) {
        setParseError(e instanceof Error ? e.message : "Invalid JSON")
        return
      }
    }

    mutation.mutate({
      id: `ua-signal-${Date.now()}`,
      configuration: configuration,
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Send automation signal</DialogTitle>
          <DialogDescription>
            {automation ? (
              <>
                <span className="font-medium text-foreground">
                  {automation.metadata.name}
                </span>
                <span className="font-mono text-xs block mt-1">
                  {automation.id}
                </span>
              </>
            ) : null}
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Signal type
            </label>
            <Select
              value={signalType}
              onValueChange={(v) =>
                handleSignalTypeChange(v as AutomationSignalType)
              }
            >
              <SelectTrigger size="sm" className="w-full max-w-none">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SIGNAL_TYPE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {signalType === "forced_trigger" && (
              <p className="text-xs text-muted-foreground">
                No payload for forced trigger.
              </p>
            )}
          </div>
          {signalTypeRequiresPayload(signalType) && (
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Signal payload (JSON)
              </label>
              <LineNumberTextarea
                className="min-h-[180px]"
                textareaClassName="min-h-[180px]"
                value={payloadText}
                onChange={(e) => {
                  setPayloadText(e.target.value)
                  setParseError(null)
                }}
              />
            </div>
          )}
          {parseError && (
            <p className="text-sm text-destructive">{parseError}</p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSend} disabled={mutation.isPending}>
            {mutation.isPending ? "Sending…" : "Send"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function AutomationsTable({
  rows,
  walletAddress,
  accountTradings,
  onSuccess,
  onStop,
  onSignal,
  readOnly = false,
}: {
  rows: AutomationState[]
  walletAddress?: string
  accountTradings: AccountTradingWithAccountId[]
  onSuccess?: () => void
  onStop?: (automation: AutomationState) => void
  onSignal?: (automation: AutomationState) => void
  readOnly?: boolean
}) {
  const [detail, setDetail] = useState<AutomationState | null>(null)
  const [signalTarget, setSignalTarget] = useState<AutomationState | null>(
    null,
  )
  const [sort, setSort] = useState<SortState<AutomationSortKey>>({
    key: "updated",
    dir: "desc",
  })
  const [filters, setFilters] = useState<ColumnFilters<AutomationSortKey>>({})

  const displayRows = useMemo(
    () => sortAutomations(filterAutomations(rows, filters), sort),
    [rows, sort, filters],
  )

  const automationColumns: AutomationSortKey[] = [
    "id",
    "status",
    "updated",
    "name",
    "progress",
    "dsl",
    "exchanges",
    "assets",
    "orders",
    "trades",
  ]

  const automationColumnCount = automationColumns.length + 1
  const actionsHeadClass = "w-32"

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        No automations.
      </p>
    )
  }

  return (
    <>
      {hasActiveFilters(filters) && (
        <div className="flex justify-end mb-2">
          <button
            type="button"
            className="text-xs text-muted-foreground hover:text-foreground hover:underline"
            onClick={() => setFilters({})}
          >
            Clear filters
          </button>
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <SortableTableHead
              label="ID"
              sortKey="id"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
              className="text-center"
            />
            <SortableTableHead
              label="St"
              sortKey="status"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
              className="text-center"
            />
            <SortableTableHead
              label="Updated"
              sortKey="updated"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
              className="text-center"
            />
            <SortableTableHead
              label="Name"
              sortKey="name"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Actions"
              sortKey="progress"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
              className={cn(AUTOMATION_COMPACT_COLUMN_CLASS, "text-center")}
            />
            <SortableTableHead
              label="Latest action"
              sortKey="dsl"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Exchange"
              sortKey="exchanges"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Assets"
              sortKey="assets"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Ordrs"
              sortKey="orders"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
              className={cn(AUTOMATION_COMPACT_COLUMN_CLASS, "text-center")}
            />
            <SortableTableHead
              label="Trds"
              sortKey="trades"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
              className={cn(AUTOMATION_COMPACT_COLUMN_CLASS, "text-center")}
            />
            <TableHead className={actionsHeadClass} />
          </TableRow>
          <TableRow className="hover:bg-transparent">
            {automationColumns.map((key) => (
              <TableHead key={key} className={automationFilterHeadClass(key)}>
                <ColumnFilterInput
                  value={filters[key] ?? ""}
                  onChange={(value) =>
                    setFilters((f) => setColumnFilter(f, key, value))
                  }
                />
              </TableHead>
            ))}
            <TableHead className={actionsHeadClass} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {displayRows.length === 0 ? (
            <TableRow>
              <TableCell
                colSpan={automationColumnCount}
                className="text-center text-sm text-muted-foreground py-8"
              >
                No rows match filters.
              </TableCell>
            </TableRow>
          ) : (
          displayRows.map((row) => {
            const canSignal = readOnly
              ? Boolean(onSignal)
              : isRunningAutomation(row)
            const canStop = readOnly ? Boolean(onStop) : isRunningAutomation(row)
            const signalButton = (
              <button
                type="button"
                className={
                  canSignal
                    ? "text-muted-foreground hover:text-foreground"
                    : "text-muted-foreground/40 cursor-not-allowed"
                }
                aria-label={readOnly ? "View signal user action" : "Send signal"}
                disabled={!canSignal}
                onClick={() => {
                  if (!canSignal) return
                  if (readOnly && onSignal) {
                    onSignal(row)
                    return
                  }
                  setSignalTarget(row)
                }}
              >
                <Zap className="size-4" />
              </button>
            )
            return (
            <TableRow key={row.id}>
              <TableCell className={debugColumnClass("center")}>
                <CenteredCellContent>
                  <CopyableIdCell id={row.id} />
                </CenteredCellContent>
              </TableCell>
              <TableCell className={debugColumnClass("center")}>
                <CenteredCellContent>
                  <DebugStatusCell
                    status={row.status}
                    extraTooltipLines={getAutomationErrorTooltipLines(row)}
                    pulseWhenRunning
                  />
                </CenteredCellContent>
              </TableCell>
              <TableCell className={debugColumnClass("center")}>
                {formatDateTime(getAutomationUpdatedAt(row))}
              </TableCell>
              <TableCell className={debugColumnClass("left")}>
                <TruncatedTextWithTooltip
                  text={row.metadata.name}
                  maxLength={AUTOMATION_NAME_DISPLAY_LENGTH}
                />
              </TableCell>
              <TableCell
                className={debugColumnClass(
                  "center",
                  `font-mono text-xs ${AUTOMATION_COMPACT_COLUMN_CLASS}`,
                )}
              >
                {formatActionProgress(row)}
              </TableCell>
              <TableCell
                className={debugColumnClass("left", "font-mono text-xs")}
              >
                <TruncatedTextWithTooltip
                  text={getAutomationDslHint(row)}
                  maxLength={LATEST_ACTION_DISPLAY_LENGTH}
                />
              </TableCell>
              <TableCell className={debugColumnClass("left")}>
                {row.exchanges?.length
                  ? row.exchanges.join(", ")
                  : "—"}
              </TableCell>
              <TableCell
                className={debugColumnClass("left", "font-mono text-xs")}
              >
                <AssetsPortfolioCell
                  assets={row.assets}
                  maxVisible={AUTOMATION_ASSETS_MAX_VISIBLE}
                />
              </TableCell>
              <TableCell
                className={debugColumnClass(
                  "center",
                  `font-mono text-xs ${AUTOMATION_COMPACT_COLUMN_CLASS}`,
                )}
              >
                <AutomationTradingCountCell
                  count={row.orders?.length ?? 0}
                  tooltip={getAutomationOrdersTooltipContent(
                    row,
                    accountTradings,
                  )}
                />
              </TableCell>
              <TableCell
                className={debugColumnClass(
                  "center",
                  `font-mono text-xs ${AUTOMATION_COMPACT_COLUMN_CLASS}`,
                )}
              >
                <AutomationTradingCountCell
                  count={row.trades?.length ?? 0}
                  tooltip={getAutomationTradesTooltipContent(
                    row,
                    accountTradings,
                  )}
                />
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2 justify-end">
                  <button
                    type="button"
                    className="text-muted-foreground hover:text-foreground"
                    aria-label="View JSON"
                    onClick={() => setDetail(row)}
                  >
                    <Eye className="size-4" />
                  </button>
                  {canSignal ? (
                    signalButton
                  ) : (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="inline-flex">{signalButton}</span>
                      </TooltipTrigger>
                      <TooltipContent side="left">
                        {readOnly
                          ? "Signal action unavailable"
                          : "Only running workflows can be signaled"}
                      </TooltipContent>
                    </Tooltip>
                  )}
                  {canStop ? (
                    <button
                      type="button"
                      className="text-muted-foreground hover:text-foreground"
                      aria-label={
                        readOnly ? "View stop user action" : "Stop automation"
                      }
                      onClick={() => onStop?.(row)}
                    >
                      <X className="size-4" />
                    </button>
                  ) : (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="inline-flex">
                          <button
                            type="button"
                            className="text-muted-foreground/40 cursor-not-allowed"
                            aria-label="Stop automation"
                            disabled
                          >
                            <X className="size-4" />
                          </button>
                        </span>
                      </TooltipTrigger>
                      <TooltipContent side="left">
                        {readOnly
                          ? "Stop action unavailable"
                          : "Only running automations can be stopped"}
                      </TooltipContent>
                    </Tooltip>
                  )}
                </div>
              </TableCell>
            </TableRow>
            )
          })
          )}
        </TableBody>
      </Table>
      <JsonDetailDialog
        title="Automation"
        data={detail}
        open={detail !== null}
        onOpenChange={(open) => {
          if (!open) setDetail(null)
        }}
      />
      {!readOnly && (
        <SignalAutomationDialog
          automation={signalTarget}
          open={signalTarget !== null}
          onOpenChange={(open) => {
            if (!open) setSignalTarget(null)
          }}
          walletAddress={walletAddress}
          onSuccess={onSuccess ?? (() => {})}
        />
      )}
    </>
  )
}

function UserActionsTable({ rows }: { rows: UserAction[] }) {
  const [detail, setDetail] = useState<UserAction | null>(null)
  const [sort, setSort] = useState<SortState<UserActionSortKey>>({
    key: "updated",
    dir: "desc",
  })
  const [filters, setFilters] = useState<ColumnFilters<UserActionSortKey>>({})

  const displayRows = useMemo(
    () => sortUserActions(filterUserActions(rows, filters), sort),
    [rows, sort, filters],
  )

  const userActionColumns: {
    key: UserActionSortKey
    placeholder?: string
  }[] = [
    { key: "id" },
    { key: "status" },
    { key: "updated" },
    { key: "actionType", placeholder: "e.g. automation_stop" },
    { key: "errorMessage" },
    { key: "errorDetails" },
  ]

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        No user actions.
      </p>
    )
  }

  return (
    <>
      {hasActiveFilters(filters) && (
        <div className="flex justify-end mb-2">
          <button
            type="button"
            className="text-xs text-muted-foreground hover:text-foreground hover:underline"
            onClick={() => setFilters({})}
          >
            Clear filters
          </button>
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <SortableTableHead
              label="ID"
              sortKey="id"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
              className="text-center"
            />
            <SortableTableHead
              label="St"
              sortKey="status"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
              className="text-center"
            />
            <SortableTableHead
              label="Updated"
              sortKey="updated"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
              className="text-center"
            />
            <SortableTableHead
              label="Action type"
              sortKey="actionType"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Error message"
              sortKey="errorMessage"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Error details"
              sortKey="errorDetails"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <TableHead className="w-12" />
          </TableRow>
          <TableRow className="hover:bg-transparent">
            {userActionColumns.map(({ key, placeholder }) => (
              <TableHead key={key} className="align-top pb-2 pt-0">
                <ColumnFilterInput
                  value={filters[key] ?? ""}
                  placeholder={placeholder}
                  onChange={(value) =>
                    setFilters((f) => setColumnFilter(f, key, value))
                  }
                />
              </TableHead>
            ))}
            <TableHead className="w-12" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {displayRows.length === 0 ? (
            <TableRow>
              <TableCell
                colSpan={7}
                className="text-center text-sm text-muted-foreground py-8"
              >
                No rows match filters.
              </TableCell>
            </TableRow>
          ) : (
          displayRows.map((row) => (
            <TableRow key={row.id}>
              <TableCell
                className={debugColumnClass("center", "font-mono text-xs")}
              >
                <TruncatedTextWithTooltip
                  text={row.id}
                  maxLength={USER_ACTION_ID_DISPLAY_LENGTH}
                />
              </TableCell>
              <TableCell className={debugColumnClass("center")}>
                <CenteredCellContent>
                  <DebugStatusCell status={row.status} />
                </CenteredCellContent>
              </TableCell>
              <TableCell className={debugColumnClass("center")}>
                {formatDateTime(getUserActionUpdatedAt(row))}
              </TableCell>
              <TableCell className={debugColumnClass("left")}>
                {getConfigurationActionType(row.configuration)}
              </TableCell>
              <TableCell className={debugColumnClass("left")}>
                {getUserActionResultErrorMessage(row.result)}
              </TableCell>
              <TableCell
                className={debugColumnClass("left", "font-mono text-xs")}
              >
                <TruncatedTextWithTooltip
                  text={getUserActionResultErrorDetails(row.result)}
                />
              </TableCell>
              <TableCell>
                <button
                  type="button"
                  className="text-muted-foreground hover:text-foreground"
                  aria-label="View JSON"
                  onClick={() => setDetail(row)}
                >
                  <Eye className="size-4" />
                </button>
              </TableCell>
            </TableRow>
          )))}
        </TableBody>
      </Table>
      <JsonDetailDialog
        title="User action"
        data={detail}
        open={detail !== null}
        onOpenChange={(open) => {
          if (!open) setDetail(null)
        }}
      />
    </>
  )
}

function AccountsTable({
  rows,
  exchangeConfigs,
  accountTradings,
  onEdit,
  onStartAutomation,
}: {
  rows: Account[]
  exchangeConfigs: ExchangeConfig[]
  accountTradings: AccountTradingWithAccountId[]
  onEdit?: (account: Account) => void
  onStartAutomation?: (account: Account) => void
}) {
  const [detail, setDetail] = useState<Account | null>(null)
  const [sort, setSort] = useState<SortState<AccountSortKey>>({
    key: "updated",
    dir: "desc",
  })
  const [filters, setFilters] = useState<ColumnFilters<AccountSortKey>>({})

  const displayRows = useMemo(
    () =>
      sortAccounts(
        filterAccounts(rows, filters, exchangeConfigs, accountTradings),
        sort,
        exchangeConfigs,
        accountTradings,
      ),
    [rows, sort, filters, exchangeConfigs, accountTradings],
  )

  const accountColumns: AccountSortKey[] = [
    "id",
    "stateStatus",
    "name",
    "exchange",
    "updated",
    "stateMessage",
    "assets",
    "orders",
    "trades",
    "simulated",
    "authenticationId",
  ]

  const accountColumnCount = accountColumns.length + 1
  const actionsHeadClass = "w-24"

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        No accounts.
      </p>
    )
  }

  return (
    <>
      {hasActiveFilters(filters) && (
        <div className="flex justify-end mb-2">
          <button
            type="button"
            className="text-xs text-muted-foreground hover:text-foreground hover:underline"
            onClick={() => setFilters({})}
          >
            Clear filters
          </button>
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <SortableTableHead
              label="ID"
              sortKey="id"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="St"
              sortKey="stateStatus"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
              className="text-center"
            />
            <SortableTableHead
              label="Name"
              sortKey="name"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Exchange"
              sortKey="exchange"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Updated"
              sortKey="updated"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="St msg"
              sortKey="stateMessage"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Assets"
              sortKey="assets"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Ordrs"
              sortKey="orders"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
              className={cn(ACCOUNT_COMPACT_COLUMN_CLASS, "text-center")}
            />
            <SortableTableHead
              label="Trds"
              sortKey="trades"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
              className={cn(ACCOUNT_COMPACT_COLUMN_CLASS, "text-center")}
            />
            <SortableTableHead
              label="Simulated"
              sortKey="simulated"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Auth ID"
              sortKey="authenticationId"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <TableHead className={actionsHeadClass} />
          </TableRow>
          <TableRow className="hover:bg-transparent">
            {accountColumns.map((key) => (
              <TableHead key={key} className={accountFilterHeadClass(key)}>
                <ColumnFilterInput
                  value={filters[key] ?? ""}
                  onChange={(value) =>
                    setFilters((f) => setColumnFilter(f, key, value))
                  }
                />
              </TableHead>
            ))}
            <TableHead className={actionsHeadClass} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {displayRows.length === 0 ? (
            <TableRow>
              <TableCell
                colSpan={accountColumnCount}
                className="text-center text-sm text-muted-foreground py-8"
              >
                No rows match filters.
              </TableCell>
            </TableRow>
          ) : (
            displayRows.map((row) => (
              <TableRow key={row.id}>
                <TableCell className={debugColumnClass("center")}>
                  <CenteredCellContent>
                    <CopyableIdCell id={row.id} />
                  </CenteredCellContent>
                </TableCell>
                <TableCell className={debugColumnClass("center")}>
                  <CenteredCellContent>
                    <DebugStatusCell
                      status={row.state?.status}
                      extraTooltipLines={
                        row.state?.message ? [row.state.message] : undefined
                      }
                    />
                  </CenteredCellContent>
                </TableCell>
                <TableCell className={debugColumnClass("left")}>
                  {row.name}
                </TableCell>
                <TableCell className={debugColumnClass("left")}>
                  {getAccountExchangeNames(row, exchangeConfigs)}
                </TableCell>
                <TableCell className={debugColumnClass("center")}>
                  {formatDateTime(row.updated_at)}
                </TableCell>
                <TableCell className={debugColumnClass("left")}>
                  {row.state?.message ?? "—"}
                </TableCell>
                <TableCell className={debugColumnClass("left")}>
                  <AssetsPortfolioCell assets={row.assets} />
                </TableCell>
                <TableCell
                  className={debugColumnClass(
                    "center",
                    `font-mono text-xs ${ACCOUNT_COMPACT_COLUMN_CLASS}`,
                  )}
                >
                  <AutomationTradingCountCell
                    count={getAccountOrdersCount(row.id, accountTradings)}
                    tooltip={getAccountOrdersTooltipContent(
                      row.id,
                      accountTradings,
                    )}
                  />
                </TableCell>
                <TableCell
                  className={debugColumnClass(
                    "center",
                    `font-mono text-xs ${ACCOUNT_COMPACT_COLUMN_CLASS}`,
                  )}
                >
                  <AutomationTradingCountCell
                    count={getAccountTradesCount(row.id, accountTradings)}
                    tooltip={getAccountTradesTooltipContent(
                      row.id,
                      accountTradings,
                    )}
                  />
                </TableCell>
                <TableCell className={debugColumnClass("center")}>
                  {row.is_simulated ? "yes" : "no"}
                </TableCell>
                <TableCell className={debugColumnClass("center")}>
                  {row.authentication_id ? (
                    <CenteredCellContent>
                      <CopyableIdCell id={row.authentication_id} />
                    </CenteredCellContent>
                  ) : (
                    "—"
                  )}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2 justify-end">
                    <button
                      type="button"
                      className="text-muted-foreground hover:text-foreground"
                      aria-label="View JSON"
                      onClick={() => setDetail(row)}
                    >
                      <Eye className="size-4" />
                    </button>
                    <button
                      type="button"
                      className="text-muted-foreground hover:text-foreground"
                      aria-label="Start automation"
                      onClick={() => onStartAutomation?.(row)}
                    >
                      <Play className="size-4" />
                    </button>
                    <button
                      type="button"
                      className="text-muted-foreground hover:text-foreground"
                      aria-label="Edit account"
                      onClick={() => onEdit?.(row)}
                    >
                      <Pencil className="size-4" />
                    </button>
                  </div>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
      <JsonDetailDialog
        title="Account"
        data={detail}
        open={detail !== null}
        onOpenChange={(open) => {
          if (!open) setDetail(null)
        }}
      />
    </>
  )
}

function ExchangeConfigsTable({
  rows,
  accounts,
  onEdit,
}: {
  rows: ExchangeConfig[]
  accounts: Account[]
  onEdit?: (config: ExchangeConfig) => void
}) {
  const [detail, setDetail] = useState<ExchangeConfig | null>(null)
  const [sort, setSort] = useState<SortState<ExchangeConfigSortKey>>({
    key: "exchange",
    dir: "asc",
  })
  const [filters, setFilters] = useState<ColumnFilters<ExchangeConfigSortKey>>({})

  const displayRows = useMemo(
    () =>
      sortExchangeConfigs(
        filterExchangeConfigs(rows, filters, accounts),
        sort,
        accounts,
      ),
    [rows, sort, filters, accounts],
  )

  const exchangeConfigColumns: ExchangeConfigSortKey[] = [
    "id",
    "exchange",
    "name",
    "accounts",
    "sandboxed",
    "url",
  ]

  const exchangeConfigColumnCount = exchangeConfigColumns.length + 1
  const actionsHeadClass = "w-24"

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        No exchange configs.
      </p>
    )
  }

  return (
    <>
      {hasActiveFilters(filters) && (
        <div className="flex justify-end mb-2">
          <button
            type="button"
            className="text-xs text-muted-foreground hover:text-foreground hover:underline"
            onClick={() => setFilters({})}
          >
            Clear filters
          </button>
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <SortableTableHead
              label="ID"
              sortKey="id"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Exchange"
              sortKey="exchange"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Name"
              sortKey="name"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Accounts"
              sortKey="accounts"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Sandboxed"
              sortKey="sandboxed"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="URL"
              sortKey="url"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <TableHead className={actionsHeadClass} />
          </TableRow>
          <TableRow className="hover:bg-transparent">
            {exchangeConfigColumns.map((key) => (
              <TableHead key={key} className="align-top pb-2 pt-0">
                <ColumnFilterInput
                  value={filters[key] ?? ""}
                  onChange={(value) =>
                    setFilters((f) => setColumnFilter(f, key, value))
                  }
                />
              </TableHead>
            ))}
            <TableHead className={actionsHeadClass} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {displayRows.length === 0 ? (
            <TableRow>
              <TableCell
                colSpan={exchangeConfigColumnCount}
                className="text-center text-sm text-muted-foreground py-8"
              >
                No rows match filters.
              </TableCell>
            </TableRow>
          ) : (
            displayRows.map((row) => (
              <TableRow key={row.id}>
                <TableCell className={debugColumnClass("center")}>
                  <CenteredCellContent>
                    <CopyableIdCell id={row.id} />
                  </CenteredCellContent>
                </TableCell>
                <TableCell className={debugColumnClass("left")}>
                  {row.exchange}
                </TableCell>
                <TableCell className={debugColumnClass("left")}>
                  {row.name}
                </TableCell>
                <TableCell className={debugColumnClass("left")}>
                  {getAccountsReferencingExchangeConfig(row.id, accounts)}
                </TableCell>
                <TableCell className={debugColumnClass("center")}>
                  {row.sandboxed ? "yes" : "no"}
                </TableCell>
                <TableCell
                  className={debugColumnClass("left", "font-mono text-xs break-all")}
                >
                  {row.url ?? "—"}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2 justify-end">
                    <button
                      type="button"
                      className="text-muted-foreground hover:text-foreground"
                      aria-label="View JSON"
                      onClick={() => setDetail(row)}
                    >
                      <Eye className="size-4" />
                    </button>
                    <button
                      type="button"
                      className="text-muted-foreground hover:text-foreground"
                      aria-label="Edit exchange config"
                      onClick={() => onEdit?.(row)}
                    >
                      <Pencil className="size-4" />
                    </button>
                  </div>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
      <JsonDetailDialog
        title="Exchange config"
        data={detail}
        open={detail !== null}
        onOpenChange={(open) => {
          if (!open) setDetail(null)
        }}
      />
    </>
  )
}

function StrategiesTable({
  rows,
  onEdit,
  onStartAutomation,
}: {
  rows: Strategy[]
  onEdit?: (strategy: Strategy) => void
  onStartAutomation?: (strategy: Strategy) => void
}) {
  const [detail, setDetail] = useState<Strategy | null>(null)
  const [sort, setSort] = useState<SortState<StrategySortKey>>({
    key: "id",
    dir: "asc",
  })
  const [filters, setFilters] = useState<ColumnFilters<StrategySortKey>>({})

  const displayRows = useMemo(
    () => sortStrategies(filterStrategies(rows, filters), sort),
    [rows, sort, filters],
  )

  const strategyColumns: StrategySortKey[] = [
    "id",
    "name",
    "version",
    "updated",
    "description",
    "referenceMarket",
    "configType",
  ]

  const strategyColumnCount = strategyColumns.length + 1
  const actionsHeadClass = "w-24"

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        No strategies.
      </p>
    )
  }

  return (
    <>
      {hasActiveFilters(filters) && (
        <div className="flex justify-end mb-2">
          <button
            type="button"
            className="text-xs text-muted-foreground hover:text-foreground hover:underline"
            onClick={() => setFilters({})}
          >
            Clear filters
          </button>
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <SortableTableHead
              label="ID"
              sortKey="id"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Name"
              sortKey="name"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Version"
              sortKey="version"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Updated"
              sortKey="updated"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Description"
              sortKey="description"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Reference market"
              sortKey="referenceMarket"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <SortableTableHead
              label="Config type"
              sortKey="configType"
              sort={sort}
              onSort={(key) => setSort((s) => toggleSort(s, key))}
            />
            <TableHead className={actionsHeadClass} />
          </TableRow>
          <TableRow className="hover:bg-transparent">
            {strategyColumns.map((key) => (
              <TableHead key={key} className="align-top pb-2 pt-0">
                <ColumnFilterInput
                  value={filters[key] ?? ""}
                  onChange={(value) =>
                    setFilters((f) => setColumnFilter(f, key, value))
                  }
                />
              </TableHead>
            ))}
            <TableHead className={actionsHeadClass} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {displayRows.length === 0 ? (
            <TableRow>
              <TableCell
                colSpan={strategyColumnCount}
                className="text-center text-sm text-muted-foreground py-8"
              >
                No rows match filters.
              </TableCell>
            </TableRow>
          ) : (
            displayRows.map((row) => (
              <TableRow key={`${row.id}-${row.version}`}>
                <TableCell className={debugColumnClass("center")}>
                  <CenteredCellContent>
                    <CopyableIdCell id={row.id} />
                  </CenteredCellContent>
                </TableCell>
                <TableCell className={debugColumnClass("left")}>
                  {row.name ?? "—"}
                </TableCell>
                <TableCell
                  className={debugColumnClass("center", "font-mono text-xs")}
                >
                  {row.version}
                </TableCell>
                <TableCell className={debugColumnClass("center")}>
                  {formatDateTime(row.updated_at)}
                </TableCell>
                <TableCell className={debugColumnClass("left")}>
                  {row.description ?? "—"}
                </TableCell>
                <TableCell className={debugColumnClass("left")}>
                  {row.reference_market}
                </TableCell>
                <TableCell className={debugColumnClass("left")}>
                  {getStrategyConfigurationType(row)}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2 justify-end">
                    <button
                      type="button"
                      className="text-muted-foreground hover:text-foreground"
                      aria-label="View JSON"
                      onClick={() => setDetail(row)}
                    >
                      <Eye className="size-4" />
                    </button>
                    <button
                      type="button"
                      className="text-muted-foreground hover:text-foreground"
                      aria-label="Start automation"
                      onClick={() => onStartAutomation?.(row)}
                    >
                      <Play className="size-4" />
                    </button>
                    <button
                      type="button"
                      className="text-muted-foreground hover:text-foreground"
                      aria-label="Edit strategy"
                      onClick={() => onEdit?.(row)}
                    >
                      <Pencil className="size-4" />
                    </button>
                  </div>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
      <JsonDetailDialog
        title="Strategy"
        data={detail}
        open={detail !== null}
        onOpenChange={(open) => {
          if (!open) setDetail(null)
        }}
      />
    </>
  )
}

function validateUserActionJson(text: string): string | null {
  const trimmed = text.trim()
  if (!trimmed) return "JSON cannot be empty"
  try {
    const parsed = JSON.parse(trimmed) as UserAction
    if (!parsed.id || typeof parsed.id !== "string") {
      return 'Payload must include a string "id" field'
    }
    return null
  } catch (e) {
    return e instanceof Error ? e.message : "Invalid JSON"
  }
}

type ExecuteActionDraft = {
  actionType: UserActionType
  jsonText: string
}

function ExecuteActionDialog({
  open,
  onOpenChange,
  walletAddress,
  onSuccess,
  draft,
  copyOnly = false,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  walletAddress?: string
  onSuccess: () => void
  draft: ExecuteActionDraft | null
  copyOnly?: boolean
}) {
  const [selectedTemplateKey, setSelectedTemplateKey] =
    useState<UserActionTemplateKey>(DEFAULT_USER_ACTION_TEMPLATE_KEY)
  const [jsonText, setJsonText] = useState(() =>
    buildUserActionTemplateJson(DEFAULT_USER_ACTION_TEMPLATE_KEY),
  )
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const validationError = useMemo(
    () => validateUserActionJson(jsonText),
    [jsonText],
  )

  useEffect(() => {
    if (open) {
      if (draft) {
        setSelectedTemplateKey(userActionTemplateKeyFromActionType(draft.actionType))
        setJsonText(draft.jsonText)
      } else {
        setSelectedTemplateKey(DEFAULT_USER_ACTION_TEMPLATE_KEY)
        setJsonText(buildUserActionTemplateJson(DEFAULT_USER_ACTION_TEMPLATE_KEY))
      }
    }
  }, [open, draft])

  const handleTemplateKeyChange = (value: UserActionTemplateKey) => {
    setSelectedTemplateKey(value)
    setJsonText(buildUserActionTemplateJson(value))
  }

  const mutation = useMutation({
    mutationFn: (body: UserAction) =>
      DebugService.executeUserAction({
        requestBody: body,
        walletAddress: walletAddress ?? null,
      }),
    onSuccess: () => {
      showSuccessToast("Action submitted")
      onOpenChange(false)
      onSuccess()
    },
    onError: (error) => {
      handleError.bind(showErrorToast)(error as ApiError)
    },
  })

  const handleRun = () => {
    if (validationError) return
    const parsed = JSON.parse(jsonText.trim()) as UserAction
    mutation.mutate(parsed)
  }

  const handleCopy = () => {
    if (validationError) return
    copyTextToClipboard(jsonText.trim(), "User action JSON")
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {copyOnly ? "User action" : "Execute user action"}
          </DialogTitle>
          <DialogDescription>
            {copyOnly
              ? "Edit the JSON below if needed, then copy it for the user to run on their node."
              : "POST a UserAction JSON body to the debug endpoint."}
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          {!copyOnly && (
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Action type
              </label>
              <Select
                value={selectedTemplateKey}
                onValueChange={(value) =>
                  handleTemplateKeyChange(value as UserActionTemplateKey)
                }
              >
                <SelectTrigger size="sm" className="w-full max-w-none">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {USER_ACTION_TEMPLATE_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          <LineNumberTextarea
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
          />
        </div>
        {validationError && (
          <p className="text-sm text-destructive">{validationError}</p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          {copyOnly ? (
            <Button onClick={handleCopy} disabled={validationError !== null}>
              <Copy className="size-4" />
              Copy
            </Button>
          ) : (
            <Button
              onClick={handleRun}
              disabled={mutation.isPending || validationError !== null}
            >
              {mutation.isPending ? "Running…" : "Run"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function formatImportedSnapshotContents(
  counts: ImportedDebugSummary["counts"],
): string {
  return [
    `${counts.automations} automations`,
    `${counts.userActions} user actions`,
    `${counts.accounts} accounts`,
    `${counts.exchangeConfigs} exchange configs`,
    `${counts.strategies} strategies`,
  ].join(", ")
}

function ImportedDebugSnapshotBanner({
  summary,
  onReturnToLive,
}: {
  summary: ImportedDebugSummary
  onReturnToLive: () => void
}) {
  const latestUpdatedLabel = summary.latestStateUpdatedAt
    ? formatDateTime(summary.latestStateUpdatedAt)
    : "—"

  return (
    <div className="flex flex-col gap-4 rounded-md border border-frost/30 bg-frost/10 p-4 text-sm sm:flex-row sm:items-start">
      <FileText className="mt-0.5 size-4 shrink-0 text-frost" />
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <p className="font-medium text-foreground">
          Imported debug snapshot (read-only)
        </p>
        <p className="text-muted-foreground">
          You are viewing a static JSON snapshot from another user&apos;s node.
          This is not live data and nothing you do here is sent to the scheduler.
          Row actions open the user-action editor so you can copy JSON to send
          back to the user.
        </p>
        <ul className="space-y-1 font-mono text-xs text-muted-foreground">
          <li>Last updated in snapshot: {latestUpdatedLabel}</li>
          <li>Imported: {formatDateTime(summary.importedAt.toISOString())}</li>
          <li>Source: {summary.sourceLabel}</li>
          <li>State schema version: {summary.version}</li>
          <li>Contents: {formatImportedSnapshotContents(summary.counts)}</li>
        </ul>
      </div>
    </div>
  )
}

function ImportDebugStateDialog({
  open,
  onOpenChange,
  onImported,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onImported: (state: DebugState, sourceLabel: string) => void
}) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [jsonText, setJsonText] = useState("")
  const [parseError, setParseError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setJsonText("")
      setParseError(null)
    }
  }, [open])

  const tryImportSnapshot = (text: string, sourceLabel: string): boolean => {
    const result = parseDebugStateJson(text)
    if ("error" in result) {
      setParseError(result.error)
      return false
    }
    onImported(result.state, sourceLabel)
    onOpenChange(false)
    toast.success("Debug snapshot imported")
    return true
  }

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    setParseError(null)
    const reader = new FileReader()
    reader.onload = () => {
      const text = typeof reader.result === "string" ? reader.result : ""
      tryImportSnapshot(text, file.name)
    }
    reader.readAsText(file)
    event.target.value = ""
  }

  const handleImport = () => {
    tryImportSnapshot(jsonText, "Pasted JSON")
  }

  const handleJsonPaste = (event: ClipboardEvent<HTMLTextAreaElement>) => {
    const pastedText = event.clipboardData.getData("text")
    if (!pastedText.trim()) return
    const result = parseDebugStateJson(pastedText)
    if ("state" in result) {
      event.preventDefault()
      tryImportSnapshot(pastedText, "Pasted JSON")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Import debug snapshot</DialogTitle>
          <DialogDescription>
            Choose a .json file to load immediately, or paste JSON below.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4 min-h-0 flex-1">
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,application/json"
            className="hidden"
            onChange={handleFileChange}
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="w-fit"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="size-4" />
            Choose file
          </Button>
          <LineNumberTextarea
            className="min-h-[240px] flex-1"
            textareaClassName="min-h-[240px]"
            value={jsonText}
            onPaste={handleJsonPaste}
            onChange={(event) => {
              setJsonText(event.target.value)
              if (parseError) setParseError(null)
            }}
          />
          {parseError && (
            <p className="text-sm text-destructive">{parseError}</p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleImport}>Import</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function DebugPage() {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const currentAddress = localStorage.getItem("auth_username") ?? ""
  const isSuperuser = user?.is_superuser === true

  const [walletAddress, setWalletAddress] = useState(currentAddress)
  const [executeOpen, setExecuteOpen] = useState(false)
  const [executeDraft, setExecuteDraft] = useState<ExecuteActionDraft | null>(
    null,
  )
  const [importOpen, setImportOpen] = useState(false)
  const [importedSnapshot, setImportedSnapshot] = useState<DebugState | null>(
    null,
  )
  const [importMeta, setImportMeta] = useState<{
    importedAt: Date
    sourceLabel: string
  } | null>(null)

  const openExecuteDialog = (draft?: ExecuteActionDraft) => {
    setExecuteDraft(draft ?? null)
    setExecuteOpen(true)
  }

  const handleExecuteOpenChange = (open: boolean) => {
    setExecuteOpen(open)
    if (!open) {
      setExecuteDraft(null)
    }
  }

  useEffect(() => {
    if (!isSuperuser) setWalletAddress(currentAddress)
  }, [currentAddress, isSuperuser])

  const walletQueryParam = useMemo(() => {
    if (!isSuperuser || !walletAddress) return undefined
    if (walletAddress.toLowerCase() === currentAddress.toLowerCase()) {
      return undefined
    }
    return walletAddress
  }, [isSuperuser, walletAddress, currentAddress])

  const { data: wallets = [] } = useQuery({
    queryKey: ["wallets"],
    queryFn: () => WalletsService.listWallets(),
    enabled: isSuperuser,
  })

  const isImportedMode = importedSnapshot !== null

  const debugQuery = useQuery({
    ...getDebugQueryOptions(walletQueryParam),
    enabled: !isImportedMode,
    retry: (failureCount, error) => {
      const status = (error as ApiError)?.status
      if (status === 503) return false
      return failureCount < 2
    },
  })

  useEffect(() => {
    if (
      !isImportedMode &&
      debugQuery.isError &&
      debugQuery.error &&
      (debugQuery.error as ApiError).status !== 503
    ) {
      handleError.bind(showErrorToast)(debugQuery.error as ApiError)
    }
  }, [isImportedMode, debugQuery.isError, debugQuery.error, showErrorToast])

  const activeDebugState = isImportedMode ? importedSnapshot : debugQuery.data

  const automations = activeDebugState?.debug?.automations ?? []
  const userActions = activeDebugState?.debug?.user_actions ?? []
  const accounts = activeDebugState?.debug?.accounts ?? []
  const exchangeConfigs = activeDebugState?.debug?.exchange_configs ?? []
  const accountTradings = activeDebugState?.debug?.account_tradings ?? []
  const localStrategies = activeDebugState?.debug?.local_strategies ?? []
  const schedulerUnavailable =
    !isImportedMode &&
    debugQuery.isError &&
    (debugQuery.error as ApiError)?.status === 503

  const importedSummary = useMemo(() => {
    if (!importedSnapshot || !importMeta) return null
    return summarizeImportedDebugState(importedSnapshot, importMeta)
  }, [importedSnapshot, importMeta])

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["debug"] })
  }

  const handleImported = (state: DebugState, sourceLabel: string) => {
    setImportedSnapshot(state)
    setImportMeta({ importedAt: new Date(), sourceLabel })
  }

  const returnToLiveView = () => {
    setImportedSnapshot(null)
    setImportMeta(null)
  }

  const handleExportSnapshot = () => {
    if (!debugQuery.data) return
    const exportWallet =
      walletAddress.trim().length > 0 ? walletAddress : currentAddress
    downloadDebugStateJson(
      debugQuery.data,
      buildDebugExportFilename(exportWallet),
    )
    showSuccessToast("Debug snapshot downloaded")
  }

  const canExportSnapshot =
    !isImportedMode && Boolean(debugQuery.data) && !schedulerUnavailable

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Bug className="size-6" />
            Debug view
          </h1>
          <div className="flex flex-wrap items-center justify-end gap-2">
            {isImportedMode ? (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setImportOpen(true)}
                >
                  <Upload className="size-4" />
                  Import
                </Button>
                <Button variant="outline" size="sm" onClick={returnToLiveView}>
                  Return to live view
                </Button>
              </>
            ) : (
              <>
                {isSuperuser && (
                  <select
                    id="debug-wallet"
                    aria-label="Wallet"
                    className="h-8 rounded-md border border-rule bg-input px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-frost max-w-xs"
                    value={walletAddress}
                    onChange={(e) => setWalletAddress(e.target.value)}
                  >
                    {wallets.map((w) => (
                      <option key={w.address} value={w.address}>
                        {w.name || truncateAddress(w.address)} (
                        {truncateAddress(w.address)})
                      </option>
                    ))}
                  </select>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setImportOpen(true)}
                >
                  <Upload className="size-4" />
                  Import
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExportSnapshot}
                  disabled={!canExportSnapshot}
                >
                  <Download className="size-4" />
                  Export
                </Button>
                <Button variant="outline" size="sm" onClick={refresh}>
                  <RefreshCw className="size-4" />
                  Refresh
                </Button>
                <Button size="sm" onClick={() => openExecuteDialog()}>
                  <Play className="size-4" />
                  Execute
                </Button>
              </>
            )}
          </div>
        </div>
        <p className="text-muted-foreground text-sm">
          Snapshot of current and historical activity. Contains no API secret
          or private keys.
          {activeDebugState?.version && (
            <span className="ml-2 font-mono text-xs">
              state v{activeDebugState.version}
            </span>
          )}
        </p>
      </div>

      {importedSummary && (
        <ImportedDebugSnapshotBanner
          summary={importedSummary}
          onReturnToLive={returnToLiveView}
        />
      )}

      {schedulerUnavailable && (
        <div className="flex items-start gap-2 rounded-md border border-warn/30 bg-warn/10 p-4 text-sm text-warn">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" />
          <span>
            Scheduler is not initialized. Debug data is unavailable until the
            node scheduler has started.
          </span>
        </div>
      )}

      {!isImportedMode && debugQuery.isLoading && !schedulerUnavailable && (
        <p className="text-sm text-muted-foreground">Loading debug state…</p>
      )}

      {(isImportedMode || (!schedulerUnavailable && !debugQuery.isLoading)) && (
        <Tabs defaultValue="automations">
          <TabsList className="flex h-auto flex-wrap gap-1">
            <TabsTrigger value="automations">
              Automations ({automations.length})
            </TabsTrigger>
            <TabsTrigger value="user-actions">
              User actions ({userActions.length})
            </TabsTrigger>
            <TabsTrigger value="accounts">
              Accounts ({accounts.length})
            </TabsTrigger>
            <TabsTrigger value="exchange-configs">
              Exchange configs ({exchangeConfigs.length})
            </TabsTrigger>
            <TabsTrigger value="strategies">
              Strategies ({localStrategies.length})
            </TabsTrigger>
          </TabsList>
          <TabsContent value="automations" className="mt-4">
            <AutomationsTable
              rows={automations}
              readOnly={isImportedMode}
              walletAddress={isImportedMode ? undefined : walletQueryParam}
              accountTradings={accountTradings}
              onSuccess={isImportedMode ? undefined : refresh}
              onSignal={
                isImportedMode
                  ? (automation) =>
                      openExecuteDialog({
                        actionType: "automation_signal",
                        jsonText: buildAutomationSignalUserActionJson(
                          automation.id,
                        ),
                      })
                  : undefined
              }
              onStop={(automation) =>
                openExecuteDialog({
                  actionType: "automation_stop",
                  jsonText: buildAutomationStopUserActionJson(automation.id),
                })
              }
            />
          </TabsContent>
          <TabsContent value="user-actions" className="mt-4">
            <UserActionsTable rows={userActions} />
          </TabsContent>
          <TabsContent value="accounts" className="mt-4">
            <AccountsTable
              rows={accounts}
              exchangeConfigs={exchangeConfigs}
              accountTradings={accountTradings}
              onEdit={(account) =>
                openExecuteDialog({
                  actionType: "account_edit",
                  jsonText: buildAccountEditUserActionJson(account),
                })
              }
              onStartAutomation={(account) =>
                openExecuteDialog({
                  actionType: "automation_create",
                  jsonText: buildAutomationCreateUserActionJsonForAccount(
                    account,
                  ),
                })
              }
            />
          </TabsContent>
          <TabsContent value="exchange-configs" className="mt-4">
            <ExchangeConfigsTable
              rows={exchangeConfigs}
              accounts={accounts}
              onEdit={(config) =>
                openExecuteDialog({
                  actionType: "exchange_config_edit",
                  jsonText: buildExchangeConfigEditUserActionJson(config),
                })
              }
            />
          </TabsContent>
          <TabsContent value="strategies" className="mt-4">
            <StrategiesTable
              rows={localStrategies}
              onEdit={(strategy) =>
                openExecuteDialog({
                  actionType: "strategy_edit",
                  jsonText: buildStrategyEditUserActionJson(strategy),
                })
              }
              onStartAutomation={(strategy) =>
                openExecuteDialog({
                  actionType: "automation_create",
                  jsonText: buildAutomationCreateUserActionJsonForStrategy(
                    strategy,
                  ),
                })
              }
            />
          </TabsContent>
        </Tabs>
      )}

      <ImportDebugStateDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        onImported={handleImported}
      />

      <ExecuteActionDialog
        open={executeOpen}
        onOpenChange={handleExecuteOpenChange}
        walletAddress={walletQueryParam}
        onSuccess={refresh}
        draft={executeDraft}
        copyOnly={isImportedMode}
      />
    </div>
  )
}
