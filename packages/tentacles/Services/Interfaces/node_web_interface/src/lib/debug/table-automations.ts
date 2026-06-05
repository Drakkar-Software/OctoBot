import type { AutomationState } from "@/client"
import {
  formatActionProgress,
  getActionExecutionStats,
  getAutomationUpdatedAt,
} from "@/lib/debug/automation"
import {
  AUTOMATION_ASSETS_MAX_VISIBLE,
  AUTOMATION_COMPACT_COLUMN_CLASS,
  AUTOMATION_COMPACT_COLUMNS,
} from "@/lib/debug/constants"
import { getAutomationDslHint } from "@/lib/debug/dsl"
import {
  countAccountAssets,
  formatAssetsSymbolsSummary,
  matchesDebugStatusColumnFilter,
} from "@/lib/debug/display-utils"
import type { AutomationSortKey } from "@/lib/debug/types"
import { formatDateTime } from "@/lib/format-datetime"
import type { ColumnFilters, SortState } from "@/lib/table-types"
import {
  compareNumbers,
  compareStrings,
  getActiveFilterKeys,
  hasActiveFilters,
  matchesTableColumnFilter,
  parseSortTime,
} from "@/lib/table"

export function automationFilterHeadClass(key: AutomationSortKey): string {
  return AUTOMATION_COMPACT_COLUMNS.has(key)
    ? `align-top pb-2 pt-0 ${AUTOMATION_COMPACT_COLUMN_CLASS}`
    : "align-top pb-2 pt-0"
}

export function automationFilterValues(
  row: AutomationState,
): Record<AutomationSortKey, string> {
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

export function filterAutomations(
  rows: AutomationState[],
  filters: ColumnFilters<AutomationSortKey>,
): AutomationState[] {
  if (!hasActiveFilters(filters)) return rows
  const activeKeys = getActiveFilterKeys(filters)
  return rows.filter((row) => {
    const values = automationFilterValues(row)
    return activeKeys.every((key) =>
      matchesTableColumnFilter(
        key,
        values,
        filters[key],
        row.status,
        matchesDebugStatusColumnFilter,
      ),
    )
  })
}

export function sortAutomations(
  rows: AutomationState[],
  sort: SortState<AutomationSortKey>,
): AutomationState[] {
  const { key, dir } = sort
  return [...rows].sort((left, right) => {
    switch (key) {
      case "id":
        return compareStrings(left.id, right.id, dir)
      case "status":
        return compareStrings(String(left.status), String(right.status), dir)
      case "name":
        return compareStrings(left.metadata.name, right.metadata.name, dir)
      case "progress": {
        const leftStats = getActionExecutionStats(left)
        const rightStats = getActionExecutionStats(right)
        const comparison = compareNumbers(leftStats.executed, rightStats.executed, dir)
        if (comparison !== 0) return comparison
        return compareNumbers(leftStats.total, rightStats.total, dir)
      }
      case "dsl":
        return compareStrings(
          getAutomationDslHint(left),
          getAutomationDslHint(right),
          dir,
        )
      case "trades":
        return compareNumbers(
          left.trades?.length ?? 0,
          right.trades?.length ?? 0,
          dir,
        )
      case "exchanges":
        return compareNumbers(
          left.exchanges?.length ?? 0,
          right.exchanges?.length ?? 0,
          dir,
        )
      case "assets":
        return compareNumbers(
          countAccountAssets(left.assets),
          countAccountAssets(right.assets),
          dir,
        )
      case "orders":
        return compareNumbers(
          left.orders?.length ?? 0,
          right.orders?.length ?? 0,
          dir,
        )
      case "updated":
        return compareNumbers(
          parseSortTime(getAutomationUpdatedAt(left)),
          parseSortTime(getAutomationUpdatedAt(right)),
          dir,
        )
      default:
        return 0
    }
  })
}
