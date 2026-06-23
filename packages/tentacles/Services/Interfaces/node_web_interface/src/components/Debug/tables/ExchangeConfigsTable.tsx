import { Eye, Pencil } from "lucide-react"
import { useMemo, useState } from "react"

import type { Account, ExchangeConfig } from "@/client"
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
  getAccountsReferencingExchangeConfig,
} from "@/lib/debug/display-utils"
import {
  filterExchangeConfigs,
  sortExchangeConfigs,
} from "@/lib/debug/table-exchange-configs"
import type { ExchangeConfigSortKey } from "@/lib/debug/types"
import { hasActiveFilters, setColumnFilter, toggleSort } from "@/lib/table"
import type { ColumnFilters, SortState } from "@/lib/table-types"

type ExchangeConfigsTableProps = {
  rows: ExchangeConfig[]
  accounts: Account[]
  onEdit?: (config: ExchangeConfig) => void
}

export function ExchangeConfigsTable({
  rows,
  accounts,
  onEdit,
}: ExchangeConfigsTableProps) {
  const [detail, setDetail] = useState<ExchangeConfig | null>(null)
  const [sort, setSort] = useState<SortState<ExchangeConfigSortKey>>({
    key: "exchange",
    dir: "asc",
  })
  const [filters, setFilters] = useState<ColumnFilters<ExchangeConfigSortKey>>(
    {},
  )

  const displayRows = useMemo(
    () =>
      sortExchangeConfigs(
        filterExchangeConfigs(rows, filters, accounts),
        sort,
        accounts,
      ),
    [rows, sort, filters, accounts],
  )

  const exchangeConfigColumns: ExchangeConfigSortKey[] = [
    "id",
    "exchange",
    "name",
    "accounts",
    "sandboxed",
    "url",
  ]

  const exchangeConfigColumnCount = exchangeConfigColumns.length + 1
  const actionsHeadClass = "w-24"

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        No exchange configs.
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
              label="Exchange"
              sortKey="exchange"
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
              label="Accounts"
              sortKey="accounts"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <SortableTableHead
              label="Sandboxed"
              sortKey="sandboxed"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <SortableTableHead
              label="URL"
              sortKey="url"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <TableHead className={actionsHeadClass} />
          </TableRow>
          <TableRow className="hover:bg-transparent">
            {exchangeConfigColumns.map((key) => (
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
                colSpan={exchangeConfigColumnCount}
                className="text-center text-sm text-muted-foreground py-8"
              >
                No rows match filters.
              </TableCell>
            </TableRow>
          ) : (
            displayRows.map((row) => (
              <TableRow key={row.id}>
                <TableCell className={debugTableCellClass("center")}>
                  <CenteredCellContent>
                    <CopyableIdCell id={row.id} />
                  </CenteredCellContent>
                </TableCell>
                <TableCell className={debugTableCellClass("left")}>
                  {row.exchange}
                </TableCell>
                <TableCell className={debugTableCellClass("left")}>
                  {row.name}
                </TableCell>
                <TableCell className={debugTableCellClass("left")}>
                  {getAccountsReferencingExchangeConfig(row.id, accounts)}
                </TableCell>
                <TableCell className={debugTableCellClass("center")}>
                  {row.sandboxed ? "yes" : "no"}
                </TableCell>
                <TableCell
                  className={debugTableCellClass(
                    "left",
                    "font-mono text-xs break-all",
                  )}
                >
                  {row.url ?? "—"}
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
                      aria-label="Edit exchange config"
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
        title="Exchange config"
        data={detail}
        open={detail !== null}
        onOpenChange={(open) => {
          if (!open) setDetail(null)
        }}
      />
    </>
  )
}
