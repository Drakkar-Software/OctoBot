import { useMemo, useState } from "react"

import type { DslKeyword } from "@/client"
import { TruncatedTextWithTooltip } from "@/components/Common/Tables/TruncatedTextWithTooltip"
import { SortableTableHead } from "@/components/Common/Tables/SortableTableHead"
import { JsonDetailDialog } from "@/components/Debug/dialogs/JsonDetailDialog"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  DSL_KEYWORD_CATEGORY_DISPLAY_LENGTH,
  DSL_KEYWORD_DESCRIPTION_DISPLAY_LENGTH,
  DSL_KEYWORD_LABEL_DISPLAY_LENGTH,
  DSL_KEYWORD_PARAMS_DISPLAY_LENGTH,
  DSL_KEYWORD_TABLE_DEFAULT_SORT,
  type DslKeywordSortKey,
} from "@/lib/dsl-keywords/constants"
import { formatDslParametersList } from "@/lib/dsl-keywords/format"
import {
  filterKeywordsBySearch,
  sortKeywords,
} from "@/lib/dsl-keywords/table-keywords"
import { debugTableCellClass } from "@/lib/debug/display-utils"
import { toggleSort } from "@/lib/table"
import type { SortState } from "@/lib/table-types"

type DslKeywordsTableProps = {
  rows: DslKeyword[]
}

export function DslKeywordsTable({ rows }: DslKeywordsTableProps) {
  const [detail, setDetail] = useState<DslKeyword | null>(null)
  const [search, setSearch] = useState("")
  const [sort, setSort] = useState<SortState<DslKeywordSortKey>>(
    DSL_KEYWORD_TABLE_DEFAULT_SORT,
  )

  const displayRows = useMemo(
    () => sortKeywords(filterKeywordsBySearch(rows, search), sort),
    [rows, search, sort],
  )

  const columnCount = 5

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        No DSL keywords.
      </p>
    )
  }

  return (
    <>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <Input
          className="max-w-md"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search name, label, description, category…"
          aria-label="Search DSL keywords"
        />
        <span className="text-sm text-muted-foreground">
          {displayRows.length} keywords
        </span>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <SortableTableHead
              label="Category"
              sortKey="category"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <SortableTableHead
              label="Label"
              sortKey="label"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <SortableTableHead
              label="Description"
              sortKey="description"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <TableHead>Inputs</TableHead>
            <TableHead>Outputs</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {displayRows.length === 0 ? (
            <TableRow>
              <TableCell
                colSpan={columnCount}
                className="text-center text-sm text-muted-foreground py-8"
              >
                No keywords match search.
              </TableCell>
            </TableRow>
          ) : (
            displayRows.map((row) => (
              <TableRow
                key={row.name}
                className="cursor-pointer"
                onClick={() => setDetail(row)}
              >
                <TableCell className={debugTableCellClass("left")}>
                  <TruncatedTextWithTooltip
                    text={row.category}
                    maxLength={DSL_KEYWORD_CATEGORY_DISPLAY_LENGTH}
                  />
                </TableCell>
                <TableCell className={debugTableCellClass("left")}>
                  <TruncatedTextWithTooltip
                    text={row.label}
                    maxLength={DSL_KEYWORD_LABEL_DISPLAY_LENGTH}
                  />
                </TableCell>
                <TableCell className={debugTableCellClass("left")}>
                  <TruncatedTextWithTooltip
                    text={row.description || "—"}
                    maxLength={DSL_KEYWORD_DESCRIPTION_DISPLAY_LENGTH}
                  />
                </TableCell>
                <TableCell className={debugTableCellClass("left")}>
                  <TruncatedTextWithTooltip
                    text={formatDslParametersList(row.inputs)}
                    maxLength={DSL_KEYWORD_PARAMS_DISPLAY_LENGTH}
                  />
                </TableCell>
                <TableCell className={debugTableCellClass("left")}>
                  <TruncatedTextWithTooltip
                    text={formatDslParametersList(row.outputs)}
                    maxLength={DSL_KEYWORD_PARAMS_DISPLAY_LENGTH}
                  />
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
      <JsonDetailDialog
        title={detail ? `DSL keyword: ${detail.name}` : "DSL keyword"}
        data={detail}
        open={detail !== null}
        onOpenChange={(open) => {
          if (!open) setDetail(null)
        }}
      />
    </>
  )
}
