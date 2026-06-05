export type SortDirection = "asc" | "desc"

export type SortState<K extends string> = {
  key: K
  dir: SortDirection
}

export type ColumnFilters<K extends string> = Partial<Record<K, string>>
