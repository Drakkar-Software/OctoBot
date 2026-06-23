import type { Strategy } from "@/client"
import { getStrategyConfigurationType } from "@/lib/debug/display-utils"
import type { StrategySortKey } from "@/lib/debug/types"
import { formatDateTime } from "@/lib/format-datetime"
import {
  compareNumbers,
  compareStrings,
  hasActiveFilters,
  matchesColumnFilter,
  parseSortTime,
} from "@/lib/table"
import type { ColumnFilters, SortState } from "@/lib/table-types"

export function strategyFilterValues(
  row: Strategy,
): Record<StrategySortKey, string> {
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

export function filterStrategies(
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

export function compareStrategiesByIdThenUpdated(
  left: Strategy,
  right: Strategy,
): number {
  const idComparison = compareStrings(left.id, right.id, "asc")
  if (idComparison !== 0) return idComparison
  return compareNumbers(
    parseSortTime(left.updated_at),
    parseSortTime(right.updated_at),
    "desc",
  )
}

export function sortStrategies(
  rows: Strategy[],
  sort: SortState<StrategySortKey>,
): Strategy[] {
  const { key, dir } = sort
  return [...rows].sort((left, right) => {
    let comparison = 0
    switch (key) {
      case "id":
        comparison = compareStrings(left.id, right.id, dir)
        break
      case "name":
        comparison = compareStrings(left.name ?? "", right.name ?? "", dir)
        break
      case "version":
        comparison = compareStrings(left.version, right.version, dir)
        break
      case "updated":
        comparison = compareNumbers(
          parseSortTime(left.updated_at),
          parseSortTime(right.updated_at),
          dir,
        )
        break
      case "description":
        comparison = compareStrings(
          left.description ?? "",
          right.description ?? "",
          dir,
        )
        break
      case "referenceMarket":
        comparison = compareStrings(
          left.reference_market,
          right.reference_market,
          dir,
        )
        break
      case "configType":
        comparison = compareStrings(
          getStrategyConfigurationType(left),
          getStrategyConfigurationType(right),
          dir,
        )
        break
      default:
        comparison = 0
    }
    if (comparison !== 0) return comparison
    return compareStrategiesByIdThenUpdated(left, right)
  })
}
