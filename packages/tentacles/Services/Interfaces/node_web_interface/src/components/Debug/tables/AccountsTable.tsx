import { Eye, Pencil, Play } from "lucide-react"
import { useMemo, useState } from "react"

import type {
  Account,
  AccountTradingWithAccountId,
  ExchangeConfig,
} from "@/client"
import { CenteredCellContent } from "@/components/Common/Tables/CenteredCellContent"
import { ClearTableFiltersButton } from "@/components/Common/Tables/ClearTableFiltersButton"
import { ColumnFilterInput } from "@/components/Common/Tables/ColumnFilterInput"
import { CopyableIdCell } from "@/components/Common/Tables/CopyableIdCell"
import { SortableTableHead } from "@/components/Common/Tables/SortableTableHead"
import { AssetsPortfolioCell } from "@/components/Debug/cells/AssetsPortfolioCell"
import { AutomationTradingCountCell } from "@/components/Debug/cells/AutomationTradingCountCell"
import { DebugStatusCell } from "@/components/Debug/cells/DebugStatusCell"
import { JsonDetailDialog } from "@/components/Debug/dialogs/JsonDetailDialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ACCOUNT_COMPACT_COLUMN_CLASS } from "@/lib/debug/constants"
import {
  debugTableCellClass,
  getAccountExchangeNames,
  getAccountOrdersCount,
  getAccountOrdersTooltipContent,
  getAccountTradesCount,
  getAccountTradesTooltipContent,
} from "@/lib/debug/display-utils"
import {
  accountFilterHeadClass,
  filterAccounts,
  sortAccounts,
} from "@/lib/debug/table-accounts"
import type { AccountSortKey } from "@/lib/debug/types"
import { formatDateTime } from "@/lib/format-datetime"
import { hasActiveFilters, setColumnFilter, toggleSort } from "@/lib/table"
import type { ColumnFilters, SortState } from "@/lib/table-types"
import { cn } from "@/lib/utils"

type AccountsTableProps = {
  rows: Account[]
  exchangeConfigs: ExchangeConfig[]
  accountTradings: AccountTradingWithAccountId[]
  onEdit?: (account: Account) => void
  onStartAutomation?: (account: Account) => void
}

export function AccountsTable({
  rows,
  exchangeConfigs,
  accountTradings,
  onEdit,
  onStartAutomation,
}: AccountsTableProps) {
  const [detail, setDetail] = useState<Account | null>(null)
  const [sort, setSort] = useState<SortState<AccountSortKey>>({
    key: "updated",
    dir: "desc",
  })
  const [filters, setFilters] = useState<ColumnFilters<AccountSortKey>>({})

  const displayRows = useMemo(
    () =>
      sortAccounts(
        filterAccounts(rows, filters, exchangeConfigs, accountTradings),
        sort,
        exchangeConfigs,
        accountTradings,
      ),
    [rows, sort, filters, exchangeConfigs, accountTradings],
  )

  const accountColumns: AccountSortKey[] = [
    "id",
    "stateStatus",
    "name",
    "exchange",
    "updated",
    "stateMessage",
    "assets",
    "orders",
    "trades",
    "simulated",
    "authenticationId",
  ]

  const accountColumnCount = accountColumns.length + 1
  const actionsHeadClass = "w-24"

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        No accounts.
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
              label="St"
              sortKey="stateStatus"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
              className="text-center"
            />
            <SortableTableHead
              label="Name"
              sortKey="name"
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
              label="Updated"
              sortKey="updated"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <SortableTableHead
              label="St msg"
              sortKey="stateMessage"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <SortableTableHead
              label="Assets"
              sortKey="assets"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <SortableTableHead
              label="Ordrs"
              sortKey="orders"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
              className={cn(ACCOUNT_COMPACT_COLUMN_CLASS, "text-center")}
            />
            <SortableTableHead
              label="Trds"
              sortKey="trades"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
              className={cn(ACCOUNT_COMPACT_COLUMN_CLASS, "text-center")}
            />
            <SortableTableHead
              label="Simulated"
              sortKey="simulated"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <SortableTableHead
              label="Auth ID"
              sortKey="authenticationId"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <TableHead className={actionsHeadClass} />
          </TableRow>
          <TableRow className="hover:bg-transparent">
            {accountColumns.map((key) => (
              <TableHead key={key} className={accountFilterHeadClass(key)}>
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
                colSpan={accountColumnCount}
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
                <TableCell className={debugTableCellClass("center")}>
                  <CenteredCellContent>
                    <DebugStatusCell
                      status={row.state?.status}
                      extraTooltipLines={
                        row.state?.message ? [row.state.message] : undefined
                      }
                    />
                  </CenteredCellContent>
                </TableCell>
                <TableCell className={debugTableCellClass("left")}>
                  {row.name}
                </TableCell>
                <TableCell className={debugTableCellClass("left")}>
                  {getAccountExchangeNames(row, exchangeConfigs)}
                </TableCell>
                <TableCell className={debugTableCellClass("center")}>
                  {formatDateTime(row.updated_at)}
                </TableCell>
                <TableCell className={debugTableCellClass("left")}>
                  {row.state?.message ?? "—"}
                </TableCell>
                <TableCell className={debugTableCellClass("left")}>
                  <AssetsPortfolioCell assets={row.assets} />
                </TableCell>
                <TableCell
                  className={debugTableCellClass(
                    "center",
                    `font-mono text-xs ${ACCOUNT_COMPACT_COLUMN_CLASS}`,
                  )}
                >
                  <AutomationTradingCountCell
                    count={getAccountOrdersCount(row.id, accountTradings)}
                    tooltip={getAccountOrdersTooltipContent(
                      row.id,
                      accountTradings,
                    )}
                  />
                </TableCell>
                <TableCell
                  className={debugTableCellClass(
                    "center",
                    `font-mono text-xs ${ACCOUNT_COMPACT_COLUMN_CLASS}`,
                  )}
                >
                  <AutomationTradingCountCell
                    count={getAccountTradesCount(row.id, accountTradings)}
                    tooltip={getAccountTradesTooltipContent(
                      row.id,
                      accountTradings,
                    )}
                  />
                </TableCell>
                <TableCell className={debugTableCellClass("center")}>
                  {row.is_simulated ? "yes" : "no"}
                </TableCell>
                <TableCell className={debugTableCellClass("center")}>
                  {row.authentication_id ? (
                    <CenteredCellContent>
                      <CopyableIdCell id={row.authentication_id} />
                    </CenteredCellContent>
                  ) : (
                    "—"
                  )}
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
                      aria-label="Edit account"
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
        title="Account"
        data={detail}
        open={detail !== null}
        onOpenChange={(open) => {
          if (!open) setDetail(null)
        }}
      />
    </>
  )
}
