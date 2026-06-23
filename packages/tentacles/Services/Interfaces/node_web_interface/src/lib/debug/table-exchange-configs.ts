import type { Account, ExchangeConfig } from "@/client"
import { getAccountsReferencingExchangeConfig } from "@/lib/debug/display-utils"
import type { ExchangeConfigSortKey } from "@/lib/debug/types"
import {
  compareNumbers,
  compareStrings,
  hasActiveFilters,
  matchesColumnFilter,
} from "@/lib/table"
import type { ColumnFilters, SortState } from "@/lib/table-types"

export function exchangeConfigFilterValues(
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

export function filterExchangeConfigs(
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

export function sortExchangeConfigs(
  rows: ExchangeConfig[],
  sort: SortState<ExchangeConfigSortKey>,
  accounts: Account[],
): ExchangeConfig[] {
  const { key, dir } = sort
  return [...rows].sort((left, right) => {
    switch (key) {
      case "id":
        return compareStrings(left.id, right.id, dir)
      case "exchange":
        return compareStrings(left.exchange, right.exchange, dir)
      case "name":
        return compareStrings(left.name, right.name, dir)
      case "accounts":
        return compareStrings(
          getAccountsReferencingExchangeConfig(left.id, accounts),
          getAccountsReferencingExchangeConfig(right.id, accounts),
          dir,
        )
      case "sandboxed":
        return compareNumbers(
          left.sandboxed ? 1 : 0,
          right.sandboxed ? 1 : 0,
          dir,
        )
      case "url":
        return compareStrings(left.url ?? "", right.url ?? "", dir)
      default:
        return 0
    }
  })
}
