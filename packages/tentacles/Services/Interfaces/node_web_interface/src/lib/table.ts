import type { ColumnFilters, SortDirection, SortState } from "@/lib/table-types"

export function parseSortTime(value: string | null | undefined): number {
  if (!value) return Number.NEGATIVE_INFINITY
  const time = new Date(value).getTime()
  return Number.isNaN(time) ? Number.NEGATIVE_INFINITY : time
}

export function compareStrings(
  left: string,
  right: string,
  direction: SortDirection,
): number {
  const comparison = left.localeCompare(right, undefined, { sensitivity: "base" })
  return direction === "asc" ? comparison : -comparison
}

export function compareNumbers(
  left: number,
  right: number,
  direction: SortDirection,
): number {
  return direction === "asc" ? left - right : right - left
}

export function toggleSort<K extends string>(
  current: SortState<K>,
  key: K,
): SortState<K> {
  if (current.key === key) {
    return { key, dir: current.dir === "asc" ? "desc" : "asc" }
  }
  return { key, dir: "asc" }
}

export function hasActiveFilters<K extends string>(
  filters: ColumnFilters<K>,
): boolean {
  return (Object.values(filters) as (string | undefined)[]).some((value) =>
    Boolean(value?.trim()),
  )
}

export function getActiveFilterKeys<K extends string>(
  filters: ColumnFilters<K>,
): K[] {
  return (Object.keys(filters) as K[]).filter((key) =>
    Boolean(filters[key]?.trim()),
  )
}

export function setColumnFilter<K extends string>(
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

export function matchesColumnFilter(
  cellText: string,
  filter: string | undefined,
): boolean {
  const query = filter?.trim().toLowerCase()
  if (!query) return true
  return cellText.toLowerCase().includes(query)
}

const DEFAULT_STATUS_COLUMN_KEYS = new Set(["status", "stateStatus"])

export function matchesTableColumnFilter(
  key: string,
  values: Record<string, string>,
  filter: string | undefined,
  rawStatus?: string | null,
  statusMatcher?: (
    status: string | null | undefined,
    columnFilter: string | undefined,
  ) => boolean,
  statusColumnKeys: ReadonlySet<string> = DEFAULT_STATUS_COLUMN_KEYS,
): boolean {
  if (statusMatcher && statusColumnKeys.has(key)) {
    return statusMatcher(rawStatus, filter)
  }
  return matchesColumnFilter(values[key] ?? "", filter)
}
