import type { DslKeyword } from "@/client"
import type { DslKeywordSortKey } from "@/lib/dsl-keywords/constants"
import { compareStrings } from "@/lib/table"
import type { SortState } from "@/lib/table-types"

export function filterKeywordsBySearch(
  rows: DslKeyword[],
  search: string,
): DslKeyword[] {
  const query = search.trim().toLowerCase()
  if (!query) return rows
  return rows.filter((row) => {
    const haystack = [
      row.name,
      row.label,
      row.description,
      row.category,
    ]
      .join(" ")
      .toLowerCase()
    return haystack.includes(query)
  })
}

export function sortKeywords(
  rows: DslKeyword[],
  sort: SortState<DslKeywordSortKey>,
): DslKeyword[] {
  const { key, dir } = sort
  return [...rows].sort((left, right) => {
    let comparison = 0
    switch (key) {
      case "name":
        comparison = compareStrings(left.name, right.name, dir)
        break
      case "category":
        comparison = compareStrings(left.category, right.category, dir)
        break
      case "label":
        comparison = compareStrings(left.label, right.label, dir)
        break
      case "description":
        comparison = compareStrings(left.description, right.description, dir)
        break
      default:
        comparison = 0
    }
    if (comparison !== 0) return comparison
    return compareStrings(left.name, right.name, "asc")
  })
}
