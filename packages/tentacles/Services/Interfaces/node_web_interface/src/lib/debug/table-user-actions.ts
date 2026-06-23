import type { UserAction } from "@/client"
import { matchesDebugStatusColumnFilter } from "@/lib/debug/display-utils"
import type { UserActionSortKey } from "@/lib/debug/types"
import {
  getConfigurationActionType,
  getUserActionResultErrorDetails,
  getUserActionResultErrorMessage,
  getUserActionUpdatedAt,
} from "@/lib/debug/user-action"
import { formatDateTime } from "@/lib/format-datetime"
import {
  compareNumbers,
  compareStrings,
  getActiveFilterKeys,
  hasActiveFilters,
  matchesTableColumnFilter,
  parseSortTime,
} from "@/lib/table"
import type { ColumnFilters, SortState } from "@/lib/table-types"

export function userActionFilterValues(
  row: UserAction,
): Record<UserActionSortKey, string> {
  return {
    id: row.id,
    status: row.status ?? "—",
    actionType: getConfigurationActionType(row.configuration),
    updated: formatDateTime(getUserActionUpdatedAt(row)),
    errorMessage: getUserActionResultErrorMessage(row.result),
    errorDetails: getUserActionResultErrorDetails(row.result),
  }
}

export function filterUserActions(
  rows: UserAction[],
  filters: ColumnFilters<UserActionSortKey>,
): UserAction[] {
  if (!hasActiveFilters(filters)) return rows
  const activeKeys = getActiveFilterKeys(filters)
  return rows.filter((row) => {
    const values = userActionFilterValues(row)
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

export function sortUserActions(
  rows: UserAction[],
  sort: SortState<UserActionSortKey>,
): UserAction[] {
  const { key, dir } = sort
  return [...rows].sort((left, right) => {
    switch (key) {
      case "id":
        return compareStrings(left.id, right.id, dir)
      case "status":
        return compareStrings(left.status ?? "", right.status ?? "", dir)
      case "actionType":
        return compareStrings(
          getConfigurationActionType(left.configuration),
          getConfigurationActionType(right.configuration),
          dir,
        )
      case "updated":
        return compareNumbers(
          parseSortTime(getUserActionUpdatedAt(left)),
          parseSortTime(getUserActionUpdatedAt(right)),
          dir,
        )
      case "errorMessage":
        return compareStrings(
          getUserActionResultErrorMessage(left.result),
          getUserActionResultErrorMessage(right.result),
          dir,
        )
      case "errorDetails":
        return compareStrings(
          getUserActionResultErrorDetails(left.result),
          getUserActionResultErrorDetails(right.result),
          dir,
        )
      default:
        return 0
    }
  })
}
