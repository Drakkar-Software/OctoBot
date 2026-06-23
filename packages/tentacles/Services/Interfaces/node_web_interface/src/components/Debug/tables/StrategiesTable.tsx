import { Eye, Pencil, Play } from "lucide-react"
import { useMemo, useState } from "react"

import type { Strategy } from "@/client"
import { CenteredCellContent } from "@/components/Common/Tables/CenteredCellContent"
import { ClearTableFiltersButton } from "@/components/Common/Tables/ClearTableFiltersButton"
import { ColumnFilterInput } from "@/components/Common/Tables/ColumnFilterInput"
import { CopyableIdCell } from "@/components/Common/Tables/CopyableIdCell"
import { SortableTableHead } from "@/components/Common/Tables/SortableTableHead"
import { JsonDetailDialog } from "@/components/Debug/dialogs/JsonDetailDialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  debugTableCellClass,
  getStrategyConfigurationType,
} from "@/lib/debug/display-utils"
import { filterStrategies, sortStrategies } from "@/lib/debug/table-strategies"
import type { StrategySortKey } from "@/lib/debug/types"
import { formatDateTime } from "@/lib/format-datetime"
import { hasActiveFilters, setColumnFilter, toggleSort } from "@/lib/table"
import type { ColumnFilters, SortState } from "@/lib/table-types"

type StrategiesTableProps = {
  rows: Strategy[]
  onEdit?: (strategy: Strategy) => void
  onStartAutomation?: (strategy: Strategy) => void
}

export function StrategiesTable({
  rows,
  onEdit,
  onStartAutomation,
}: StrategiesTableProps) {
  const [detail, setDetail] = useState<Strategy | null>(null)
  const [sort, setSort] = useState<SortState<StrategySortKey>>({
    key: "id",
    dir: "asc",
  })
  const [filters, setFilters] = useState<ColumnFilters<StrategySortKey>>({})

  const displayRows = useMemo(
    () => sortStrategies(filterStrategies(rows, filters), sort),
    [rows, sort, filters],
  )

  const strategyColumns: StrategySortKey[] = [
    "id",
    "name",
    "version",
    "updated",
    "description",
    "referenceMarket",
    "configType",
  ]

  const strategyColumnCount = strategyColumns.length + 1
  const actionsHeadClass = "w-24"

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        No strategies.
      </p>
    )
  }

  return (
    <>
      {hasActiveFilters(filters) && (
        <ClearTableFiltersButton onClear={() => setFilters({})} />
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <SortableTableHead
              label="ID"
              sortKey="id"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <SortableTableHead
              label="Name"
              sortKey="name"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <SortableTableHead
              label="Version"
              sortKey="version"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <SortableTableHead
              label="Updated"
              sortKey="updated"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <SortableTableHead
              label="Description"
              sortKey="description"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <SortableTableHead
              label="Reference market"
              sortKey="referenceMarket"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <SortableTableHead
              label="Config type"
              sortKey="configType"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <TableHead className={actionsHeadClass} />
          </TableRow>
          <TableRow className="hover:bg-transparent">
            {strategyColumns.map((key) => (
              <TableHead key={key} className="align-top pb-2 pt-0">
                <ColumnFilterInput
                  value={filters[key] ?? ""}
                  onChange={(value) =>
                    setFilters((current) =>
                      setColumnFilter(current, key, value),
                    )
                  }
                />
              </TableHead>
            ))}
            <TableHead className={actionsHeadClass} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {displayRows.length === 0 ? (
            <TableRow>
              <TableCell
                colSpan={strategyColumnCount}
                className="text-center text-sm text-muted-foreground py-8"
              >
                No rows match filters.
              </TableCell>
            </TableRow>
          ) : (
            displayRows.map((row) => (
              <TableRow key={`${row.id}-${row.version}`}>
                <TableCell className={debugTableCellClass("center")}>
                  <CenteredCellContent>
                    <CopyableIdCell id={row.id} />
                  </CenteredCellContent>
                </TableCell>
                <TableCell className={debugTableCellClass("left")}>
                  {row.name ?? "—"}
                </TableCell>
                <TableCell
                  className={debugTableCellClass("center", "font-mono text-xs")}
                >
                  {row.version}
                </TableCell>
                <TableCell className={debugTableCellClass("center")}>
                  {formatDateTime(row.updated_at)}
                </TableCell>
                <TableCell className={debugTableCellClass("left")}>
                  {row.description ?? "—"}
                </TableCell>
                <TableCell className={debugTableCellClass("left")}>
                  {row.reference_market}
                </TableCell>
                <TableCell className={debugTableCellClass("left")}>
                  {getStrategyConfigurationType(row)}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2 justify-end">
                    <button
                      type="button"
                      className="text-muted-foreground hover:text-foreground"
                      aria-label="View JSON"
                      onClick={() => setDetail(row)}
                    >
                      <Eye className="size-4" />
                    </button>
                    <button
                      type="button"
                      className="text-muted-foreground hover:text-foreground"
                      aria-label="Start automation"
                      onClick={() => onStartAutomation?.(row)}
                    >
                      <Play className="size-4" />
                    </button>
                    <button
                      type="button"
                      className="text-muted-foreground hover:text-foreground"
                      aria-label="Edit strategy"
                      onClick={() => onEdit?.(row)}
                    >
                      <Pencil className="size-4" />
                    </button>
                  </div>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
      <JsonDetailDialog
        title="Strategy"
        data={detail}
        open={detail !== null}
        onOpenChange={(open) => {
          if (!open) setDetail(null)
        }}
      />
    </>
  )
}
