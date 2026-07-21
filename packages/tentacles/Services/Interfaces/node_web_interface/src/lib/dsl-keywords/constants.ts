import type { SortState } from "@/lib/table-types"

export type DslKeywordSortKey =
  | "name"
  | "category"
  | "label"
  | "description"

export const DSL_KEYWORD_TABLE_DEFAULT_SORT: SortState<DslKeywordSortKey> = {
  key: "name",
  dir: "asc",
}

export const DSL_KEYWORD_CATEGORY_DISPLAY_LENGTH = 20
export const DSL_KEYWORD_LABEL_DISPLAY_LENGTH = 30
export const DSL_KEYWORD_DESCRIPTION_DISPLAY_LENGTH = 50
export const DSL_KEYWORD_PARAMS_DISPLAY_LENGTH = 50
