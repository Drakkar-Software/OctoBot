import type {
  Account,
  AccountTradingWithAccountId,
  ExchangeConfig,
} from "@/client"
import {
  ACCOUNT_COMPACT_COLUMN_CLASS,
  ACCOUNT_COMPACT_COLUMNS,
} from "@/lib/debug/constants"
import {
  countAccountAssets,
  formatAssetsSymbolsSummary,
  getAccountExchangeNames,
  getAccountOrdersCount,
  getAccountTradesCount,
  matchesDebugStatusColumnFilter,
} from "@/lib/debug/display-utils"
import type { AccountSortKey } from "@/lib/debug/types"
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

export function accountFilterHeadClass(key: AccountSortKey): string {
  return ACCOUNT_COMPACT_COLUMNS.has(key)
    ? `align-top pb-2 pt-0 ${ACCOUNT_COMPACT_COLUMN_CLASS}`
    : "align-top pb-2 pt-0"
}

export function accountFilterValues(
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

export function filterAccounts(
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
        matchesDebugStatusColumnFilter,
      ),
    )
  })
}

export function sortAccounts(
  rows: Account[],
  sort: SortState<AccountSortKey>,
  exchangeConfigs: ExchangeConfig[],
  accountTradings: AccountTradingWithAccountId[],
): Account[] {
  const { key, dir } = sort
  return [...rows].sort((left, right) => {
    switch (key) {
      case "id":
        return compareStrings(left.id, right.id, dir)
      case "authenticationId":
        return compareStrings(
          left.authentication_id ?? "",
          right.authentication_id ?? "",
          dir,
        )
      case "name":
        return compareStrings(left.name, right.name, dir)
      case "updated":
        return compareNumbers(
          parseSortTime(left.updated_at),
          parseSortTime(right.updated_at),
          dir,
        )
      case "stateStatus":
        return compareStrings(
          left.state?.status ?? "",
          right.state?.status ?? "",
          dir,
        )
      case "stateMessage":
        return compareStrings(
          left.state?.message ?? "",
          right.state?.message ?? "",
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
          getAccountOrdersCount(left.id, accountTradings),
          getAccountOrdersCount(right.id, accountTradings),
          dir,
        )
      case "trades":
        return compareNumbers(
          getAccountTradesCount(left.id, accountTradings),
          getAccountTradesCount(right.id, accountTradings),
          dir,
        )
      case "simulated":
        return compareNumbers(
          left.is_simulated ? 1 : 0,
          right.is_simulated ? 1 : 0,
          dir,
        )
      case "exchange":
        return compareStrings(
          getAccountExchangeNames(left, exchangeConfigs),
          getAccountExchangeNames(right, exchangeConfigs),
          dir,
        )
      default:
        return 0
    }
  })
}
