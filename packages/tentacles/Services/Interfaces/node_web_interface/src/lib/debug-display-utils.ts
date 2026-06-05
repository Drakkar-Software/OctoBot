import type {
  Account,
  AccountTradingWithAccountId,
  AutomationState,
  DetailedAsset,
  DetailedAssetsForTradingType,
  ExchangeConfig,
  Order,
  OrderSummary,
  Strategy,
  Trade,
  TradeSummary,
} from "@/client"
import { resolveOneOfInstance } from "@/lib/debug-protocol-oneof"

export function getAccountExchangeConfigIds(account: Account): string[] {
  const specifics = account.specifics
  if (!specifics || typeof specifics !== "object") return []

  const instance = resolveOneOfInstance<{ exchange_config_ids?: string[] }>(
    specifics,
  )
  if (instance?.exchange_config_ids?.length) {
    return instance.exchange_config_ids
  }

  const directIds = (specifics as { exchange_config_ids?: unknown })
    .exchange_config_ids
  if (!Array.isArray(directIds)) return []
  return directIds.filter((id): id is string => typeof id === "string")
}

export function formatAssetsPerTradingType(
  assets: Array<DetailedAssetsForTradingType> | null | undefined,
): string {
  if (!assets?.length) return "—"
  return assets
    .map((entry) => `${entry.trading_type}: ${entry.assets?.length ?? 0}`)
    .join(", ")
}

export type AssetsListEntry = DetailedAsset | DetailedAssetsForTradingType

/** Account assets are grouped by trading type; automation assets are a flat DetailedAsset list. */
function isFlatDetailedAsset(entry: AssetsListEntry): entry is DetailedAsset {
  if (!entry || typeof entry !== "object") return false
  if (!("symbol" in entry) || typeof entry.symbol !== "string") return false
  if ("assets" in entry && Array.isArray(entry.assets)) return false
  return true
}

function isGroupedAssetsForTradingType(
  entry: AssetsListEntry,
): entry is DetailedAssetsForTradingType {
  return (
    !isFlatDetailedAsset(entry) &&
    "trading_type" in entry &&
    Array.isArray(entry.assets)
  )
}

export function countAccountAssets(
  assets: Array<AssetsListEntry> | null | undefined,
): number {
  return flattenDetailedAssets(assets).length
}

export function flattenDetailedAssets(
  assets: Array<AssetsListEntry> | null | undefined,
): DetailedAsset[] {
  if (!assets?.length) return []
  const flat: DetailedAsset[] = []
  for (const entry of assets) {
    if (isFlatDetailedAsset(entry)) {
      flat.push(entry)
    } else if (entry.assets?.length) {
      flat.push(...entry.assets)
    }
  }
  return flat
}

export function formatAssetsSymbolsSummary(
  assets: Array<AssetsListEntry> | null | undefined,
  maxVisible = 3,
): string {
  const flat = flattenDetailedAssets(assets)
  if (!flat.length) return "—"
  const symbols = flat.map((asset) => asset.symbol)
  if (symbols.length <= maxVisible) {
    return symbols.join(", ")
  }
  const visible = symbols.slice(0, maxVisible)
  const remaining = symbols.length - maxVisible
  return `${visible.join(", ")} +${remaining}`
}

export function getTradingSummariesForAutomation(
  automation: AutomationState,
  summaries: Array<AccountTradingWithAccountId> | null | undefined,
): AccountTradingWithAccountId[] {
  const accountIds = automation.exchange_account_ids ?? []
  if (!accountIds.length || !summaries?.length) return []
  const idSet = new Set(accountIds)
  return summaries.filter((summary) => idSet.has(summary.account_id))
}

function buildTradingSummaryIdSet<T extends { id: string }>(
  summaries: T[],
): Set<string> {
  return new Set(summaries.map((summary) => summary.id))
}

function tradeBelongsToAutomationSummaries(
  trade: Trade,
  summaryIds: Set<string>,
): boolean {
  return summaryIds.has(trade.trade_id) || summaryIds.has(trade.id)
}

function orderBelongsToAutomationSummaries(
  order: Order,
  summaryIds: Set<string>,
): boolean {
  return summaryIds.has(order.exchange_id) || summaryIds.has(order.id)
}

function filterTradesToAutomationSummaries(
  trades: Trade[],
  automationTradeSummaries: TradeSummary[],
): Trade[] {
  const summaryIds = buildTradingSummaryIdSet(automationTradeSummaries)
  if (!summaryIds.size) return trades
  return trades.filter((trade) =>
    tradeBelongsToAutomationSummaries(trade, summaryIds),
  )
}

function filterOrdersToAutomationSummaries(
  orders: Order[],
  automationOrderSummaries: OrderSummary[],
): Order[] {
  const summaryIds = buildTradingSummaryIdSet(automationOrderSummaries)
  if (!summaryIds.size) return orders
  return orders.filter((order) =>
    orderBelongsToAutomationSummaries(order, summaryIds),
  )
}

export function getDetailedOrdersForAutomation(
  automation: AutomationState,
  summaries: Array<AccountTradingWithAccountId> | null | undefined,
): Order[] {
  const detailed = getTradingSummariesForAutomation(automation, summaries).flatMap(
    (summary) => summary.account_trading?.orders ?? [],
  )
  return filterOrdersToAutomationSummaries(detailed, automation.orders ?? [])
}

export function getDetailedTradesForAutomation(
  automation: AutomationState,
  summaries: Array<AccountTradingWithAccountId> | null | undefined,
): Trade[] {
  const detailed = getTradingSummariesForAutomation(automation, summaries).flatMap(
    (summary) => summary.account_trading?.trades ?? [],
  )
  return filterTradesToAutomationSummaries(detailed, automation.trades ?? [])
}

export function getAccountTradingForAccountId(
  accountId: string,
  summaries: Array<AccountTradingWithAccountId> | null | undefined,
): AccountTradingWithAccountId | undefined {
  return summaries?.find((summary) => summary.account_id === accountId)
}

export function getAccountOrdersCount(
  accountId: string,
  summaries: Array<AccountTradingWithAccountId> | null | undefined,
): number {
  return (
    getAccountTradingForAccountId(accountId, summaries)?.account_trading
      ?.orders?.length ?? 0
  )
}

export function getAccountTradesCount(
  accountId: string,
  summaries: Array<AccountTradingWithAccountId> | null | undefined,
): number {
  return (
    getAccountTradingForAccountId(accountId, summaries)?.account_trading
      ?.trades?.length ?? 0
  )
}

export function getAccountOrdersTooltipContent(
  accountId: string,
  summaries: Array<AccountTradingWithAccountId> | null | undefined,
): string | null {
  const matched = getAccountTradingForAccountId(accountId, summaries)
  const orders = matched?.account_trading?.orders ?? []
  if (!orders.length) return null
  return formatOrdersTradingTooltip(orders, matched ? [matched] : undefined)
}

export function getAccountTradesTooltipContent(
  accountId: string,
  summaries: Array<AccountTradingWithAccountId> | null | undefined,
): string | null {
  const matched = getAccountTradingForAccountId(accountId, summaries)
  const trades = matched?.account_trading?.trades ?? []
  if (!trades.length) return null
  return formatTradesTradingTooltip(trades, matched ? [matched] : undefined)
}

const TRADING_TOOLTIP_DATE_TIME_FORMATTER = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "numeric",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  second: "2-digit",
})

function formatTradingTooltipDateTime(value: string): string {
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : TRADING_TOOLTIP_DATE_TIME_FORMATTER.format(d)
}

function parseTradingTooltipDateMs(value: string): number {
  const milliseconds = new Date(value).getTime()
  return Number.isNaN(milliseconds) ? 0 : milliseconds
}

function sortOrdersForTooltip(orders: Order[]): Order[] {
  return [...orders].sort((left, right) => {
    const bySymbol = left.symbol.localeCompare(right.symbol)
    if (bySymbol !== 0) return bySymbol

    const byPrice = right.price - left.price
    if (byPrice !== 0) return byPrice

    return (
      parseTradingTooltipDateMs(right.created_at) -
      parseTradingTooltipDateMs(left.created_at)
    )
  })
}

function sortTradesForTooltip(trades: Trade[]): Trade[] {
  return [...trades].sort(
    (left, right) =>
      parseTradingTooltipDateMs(right.executed_at) -
      parseTradingTooltipDateMs(left.executed_at),
  )
}

function formatOrderLine(order: Order): string {
  return `${order.side.toUpperCase()} ${order.type.toUpperCase()} ${order.quantity} ${order.symbol} @ ${order.price} created: ${formatTradingTooltipDateTime(order.created_at)}`
}

function formatTradeLine(trade: Trade): string {
  return `${trade.side.toUpperCase()} ${trade.type.toUpperCase()} ${trade.quantity} ${trade.symbol} @ ${trade.price} executed: ${formatTradingTooltipDateTime(trade.executed_at)}`
}

function formatOrderSummaryLine(summary: OrderSummary): string {
  return `${summary.id} ${summary.symbol}`
}

function formatTradeSummaryLine(summary: TradeSummary): string {
  return `${summary.id} ${summary.symbol}`
}

function formatAutomationOrderSummariesTooltip(
  summaries: OrderSummary[],
): string | null {
  if (!summaries.length) return null
  return [...summaries]
    .sort((left, right) => left.symbol.localeCompare(right.symbol))
    .map(formatOrderSummaryLine)
    .join("\n")
}

function formatAutomationTradeSummariesTooltip(
  summaries: TradeSummary[],
): string | null {
  if (!summaries.length) return null
  return [...summaries]
    .sort((left, right) => left.symbol.localeCompare(right.symbol))
    .map(formatTradeSummaryLine)
    .join("\n")
}

function formatTradingBlocksFromSummaries<T>(
  matchedSummaries: AccountTradingWithAccountId[],
  getItems: (summary: AccountTradingWithAccountId) => T[] | null | undefined,
  formatLine: (item: T) => string,
): string | null {
  const withItems = matchedSummaries.filter(
    (summary) => (getItems(summary)?.length ?? 0) > 0,
  )
  if (!withItems.length) return null

  const showAccountHeaders = withItems.length > 1
  const blocks: string[] = []
  for (const summary of withItems) {
    if (showAccountHeaders) {
      blocks.push(`${summary.account_id}:`)
    }
    for (const item of getItems(summary) ?? []) {
      blocks.push(formatLine(item))
    }
    if (showAccountHeaders) {
      blocks.push("")
    }
  }
  const text = blocks.join("\n").trim()
  return text.length > 0 ? text : null
}

export function formatOrdersTradingTooltip(
  orders: Order[],
  matchedSummaries?: AccountTradingWithAccountId[],
): string | null {
  if (!orders.length) return null

  if (matchedSummaries?.length) {
    const fromSummaries = formatTradingBlocksFromSummaries(
      matchedSummaries,
      (summary) =>
        sortOrdersForTooltip(summary.account_trading?.orders ?? []),
      formatOrderLine,
    )
    if (fromSummaries) return fromSummaries
  }

  return sortOrdersForTooltip(orders).map(formatOrderLine).join("\n\n")
}

export function formatTradesTradingTooltip(
  trades: Trade[],
  matchedSummaries?: AccountTradingWithAccountId[],
): string | null {
  if (!trades.length) return null

  if (matchedSummaries?.length) {
    const fromSummaries = formatTradingBlocksFromSummaries(
      matchedSummaries,
      (summary) =>
        sortTradesForTooltip(summary.account_trading?.trades ?? []),
      formatTradeLine,
    )
    if (fromSummaries) return fromSummaries
  }

  return sortTradesForTooltip(trades).map(formatTradeLine).join("\n\n")
}

function formatAutomationFilteredOrdersTooltip(
  matched: AccountTradingWithAccountId[],
  automationOrderSummaries: OrderSummary[],
): string | null {
  const summaryIds = buildTradingSummaryIdSet(automationOrderSummaries)
  return formatTradingBlocksFromSummaries(
    matched,
    (summary) => {
      const orders = summary.account_trading?.orders ?? []
      if (!summaryIds.size) return sortOrdersForTooltip(orders)
      return sortOrdersForTooltip(
        orders.filter((order) =>
          orderBelongsToAutomationSummaries(order, summaryIds),
        ),
      )
    },
    formatOrderLine,
  )
}

function formatAutomationFilteredTradesTooltip(
  matched: AccountTradingWithAccountId[],
  automationTradeSummaries: TradeSummary[],
): string | null {
  const summaryIds = buildTradingSummaryIdSet(automationTradeSummaries)
  return formatTradingBlocksFromSummaries(
    matched,
    (summary) => {
      const trades = summary.account_trading?.trades ?? []
      if (!summaryIds.size) return sortTradesForTooltip(trades)
      return sortTradesForTooltip(
        trades.filter((trade) =>
          tradeBelongsToAutomationSummaries(trade, summaryIds),
        ),
      )
    },
    formatTradeLine,
  )
}

export function getAutomationOrdersTooltipContent(
  automation: AutomationState,
  summaries: Array<AccountTradingWithAccountId> | null | undefined,
): string | null {
  const automationOrderSummaries = automation.orders ?? []
  const matched = getTradingSummariesForAutomation(automation, summaries)
  const summaryIds = buildTradingSummaryIdSet(automationOrderSummaries)
  const detailed = matched.flatMap(
    (summary) => summary.account_trading?.orders ?? [],
  )
  const filtered = summaryIds.size
    ? filterOrdersToAutomationSummaries(detailed, automationOrderSummaries)
    : detailed
  if (filtered.length) {
    return formatAutomationFilteredOrdersTooltip(
      matched,
      automationOrderSummaries,
    )
  }
  return formatAutomationOrderSummariesTooltip(automationOrderSummaries)
}

export function getAutomationTradesTooltipContent(
  automation: AutomationState,
  summaries: Array<AccountTradingWithAccountId> | null | undefined,
): string | null {
  const automationTradeSummaries = automation.trades ?? []
  const matched = getTradingSummariesForAutomation(automation, summaries)
  const summaryIds = buildTradingSummaryIdSet(automationTradeSummaries)
  const detailed = matched.flatMap(
    (summary) => summary.account_trading?.trades ?? [],
  )
  const filtered = summaryIds.size
    ? filterTradesToAutomationSummaries(detailed, automationTradeSummaries)
    : detailed
  if (filtered.length) {
    return formatAutomationFilteredTradesTooltip(
      matched,
      automationTradeSummaries,
    )
  }
  return formatAutomationTradeSummariesTooltip(automationTradeSummaries)
}

export function formatAssetsPortfolioTooltip(
  assets: Array<AssetsListEntry> | null | undefined,
): string | null {
  if (!assets?.length) return null

  const groupedEntries = assets.filter(
    (entry): entry is DetailedAssetsForTradingType =>
      isGroupedAssetsForTradingType(entry) && (entry.assets?.length ?? 0) > 0,
  )

  if (groupedEntries.length > 0) {
    const lines: string[] = []
    const showTradingTypeHeaders = groupedEntries.length > 1
    for (const entry of groupedEntries) {
      if (showTradingTypeHeaders) {
        lines.push(`${entry.trading_type}:`)
      }
      for (const asset of entry.assets ?? []) {
        lines.push(`${asset.symbol}: ${asset.available}/${asset.total}`)
      }
    }
    return lines.length > 0 ? lines.join("\n") : null
  }

  const flat = flattenDetailedAssets(assets)
  if (!flat.length) return null
  return flat
    .map((asset) => `${asset.symbol}: ${asset.available}/${asset.total}`)
    .join("\n")
}

/** Exchange ids from bound exchange_config(s), or "—" when none are linked. */
export function getAccountExchangeNames(
  account: Account,
  exchangeConfigs: ExchangeConfig[],
): string {
  const configIds = getAccountExchangeConfigIds(account)
  if (!configIds.length) return "—"

  const exchanges = configIds
    .map(
      (configId) =>
        exchangeConfigs.find((config) => config.id === configId)?.exchange,
    )
    .filter((exchange): exchange is string => exchange != null && exchange !== "")
  if (!exchanges.length) return "—"
  return [...new Set(exchanges)].join(", ")
}

export function getAccountsReferencingExchangeConfig(
  configId: string,
  accounts: Account[],
): string {
  const names = accounts
    .filter((account) => getAccountExchangeConfigIds(account).includes(configId))
    .map((account) => account.name)
  if (!names.length) return "—"
  return names.join(", ")
}

export function getStrategyConfigurationType(strategy: Strategy): string {
  const instance = resolveOneOfInstance<{ configuration_type?: string }>(
    strategy.configuration,
  )
  if (!instance?.configuration_type) return "—"
  return String(instance.configuration_type)
}

export type DebugStatusDisplay = {
  emoji: string
  label: string
}

const DEBUG_STATUS_EMOJI: Record<string, string> = {
  running: "🟢",
  completed: "✅",
  failed: "🔴",
  pending: "🟡",
  scheduled: "🔵",
  periodic: "🔵",
  canceled: "⚪",
  valid: "🟢",
  invalid: "🔴",
  unknown: "🟡",
}

const DEBUG_STATUS_LABELS: Record<string, string> = {
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  pending: "Pending",
  scheduled: "Scheduled",
  periodic: "Recurring",
  canceled: "Canceled",
  valid: "Valid",
  invalid: "Invalid",
  unknown: "Unknown",
}

function formatStatusLabel(status: string): string {
  return DEBUG_STATUS_LABELS[status] ?? status.replace(/_/g, " ")
}

export function getDebugStatusDisplay(
  status: string | null | undefined,
): DebugStatusDisplay {
  if (!status) {
    return { emoji: "➖", label: "—" }
  }
  const normalized = status.toLowerCase()
  return {
    emoji: DEBUG_STATUS_EMOJI[normalized] ?? "➖",
    label: formatStatusLabel(normalized),
  }
}

export function formatDebugStatusTooltip(
  status: string | null | undefined,
  extraLines?: string[],
): string {
  const { label } = getDebugStatusDisplay(status)
  const lines = [label]
  if (extraLines?.length) {
    lines.push(...extraLines.filter((line) => line.length > 0))
  }
  return lines.join("\n")
}

/** Searchable text for column filters (raw value + human label). */
export function formatDebugStatusFilterText(
  status: string | null | undefined,
): string {
  const raw = status?.trim() ?? ""
  const { label } = getDebugStatusDisplay(status)
  if (!raw) return label === "—" ? "" : label
  if (label === "—" || label.toLowerCase() === raw.toLowerCase()) return raw
  return `${raw} ${label}`
}

const DEBUG_KNOWN_STATUS_TOKENS = new Set([
  "pending",
  "running",
  "completed",
  "failed",
  "scheduled",
  "periodic",
  "canceled",
  "valid",
  "invalid",
  "unknown",
])

export function matchesColumnFilter(
  cellText: string,
  filter: string | undefined,
): boolean {
  const q = filter?.trim().toLowerCase()
  if (!q) return true
  return cellText.toLowerCase().includes(q)
}

/** Status filters use exact match for known tokens to avoid cross-column substring noise. */

export type DebugTableColumnAlign = "left" | "center"

export function getDebugTableColumnAlignClass(
  align: DebugTableColumnAlign,
): string {
  return align === "center" ? "text-center" : ""
}

export function debugTableCellClass(
  align: DebugTableColumnAlign,
  ...extra: Array<string | undefined>
): string {
  const parts = [getDebugTableColumnAlignClass(align), ...extra].filter(Boolean)
  return parts.join(" ")
}

export function matchesDebugStatusColumnFilter(
  status: string | null | undefined,
  filter: string | undefined,
): boolean {
  const q = filter?.trim().toLowerCase()
  if (!q) return true
  const raw = (status ?? "").trim().toLowerCase()
  const { label } = getDebugStatusDisplay(status)
  const labelLower = label.toLowerCase()
  if (DEBUG_KNOWN_STATUS_TOKENS.has(q)) {
    return raw === q
  }
  const searchable = formatDebugStatusFilterText(status).toLowerCase()
  return searchable.includes(q) || labelLower.includes(q)
}
