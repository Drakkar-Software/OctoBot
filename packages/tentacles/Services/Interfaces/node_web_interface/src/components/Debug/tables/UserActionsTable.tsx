import { Eye } from "lucide-react"
import { useMemo, useState } from "react"

import type { UserAction } from "@/client"
import { CenteredCellContent } from "@/components/Common/Tables/CenteredCellContent"
import { ClearTableFiltersButton } from "@/components/Common/Tables/ClearTableFiltersButton"
import { ColumnFilterInput } from "@/components/Common/Tables/ColumnFilterInput"
import { SortableTableHead } from "@/components/Common/Tables/SortableTableHead"
import { TableSelectionCell } from "@/components/Common/Tables/TableSelectionCell"
import { TableSelectionHeader } from "@/components/Common/Tables/TableSelectionHeader"
import { TruncatedTextWithTooltip } from "@/components/Common/Tables/TruncatedTextWithTooltip"
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
import { USER_ACTION_ID_DISPLAY_LENGTH } from "@/lib/debug/constants"
import { debugTableCellClass } from "@/lib/debug/display-utils"
import {
  filterUserActions,
  sortUserActions,
} from "@/lib/debug/table-user-actions"
import type { UserActionSortKey } from "@/lib/debug/types"
import {
  getConfigurationActionType,
  getUserActionResultErrorDetails,
  getUserActionResultErrorMessage,
  getUserActionUpdatedAt,
} from "@/lib/debug/user-action"
import { formatDateTime } from "@/lib/format-datetime"
import { hasActiveFilters, setColumnFilter, toggleSort } from "@/lib/table"
import type { ColumnFilters, SortState } from "@/lib/table-types"

type UserActionsTableProps = {
  rows: UserAction[]
  selectionMode?: boolean
  selectedIds?: Set<string>
  onToggleRow?: (id: string) => void
  onToggleAllVisible?: (ids: string[], select: boolean) => void
}

export function UserActionsTable({
  rows,
  selectionMode = false,
  selectedIds,
  onToggleRow,
  onToggleAllVisible,
}: UserActionsTableProps) {
  const [detail, setDetail] = useState<UserAction | null>(null)
  const [sort, setSort] = useState<SortState<UserActionSortKey>>({
    key: "updated",
    dir: "desc",
  })
  const [filters, setFilters] = useState<ColumnFilters<UserActionSortKey>>({})

  const displayRows = useMemo(
    () => sortUserActions(filterUserActions(rows, filters), sort),
    [rows, sort, filters],
  )

  const visibleRowIds = useMemo(
    () => displayRows.map((row) => row.id),
    [displayRows],
  )

  const userActionColumns: {
    key: UserActionSortKey
    placeholder?: string
  }[] = [
    { key: "id" },
    { key: "status" },
    { key: "updated" },
    { key: "actionType", placeholder: "e.g. automation_stop" },
    { key: "errorMessage" },
    { key: "errorDetails" },
  ]

  const columnCount =
    userActionColumns.length + 1 + (selectionMode ? 1 : 0)

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        No user actions.
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
            {selectionMode && selectedIds && onToggleAllVisible && (
              <TableSelectionHeader
                visibleIds={visibleRowIds}
                selectedIds={selectedIds}
                onToggleAllVisible={onToggleAllVisible}
              />
            )}
            <SortableTableHead
              label="ID"
              sortKey="id"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
              className="text-center"
            />
            <SortableTableHead
              label="St"
              sortKey="status"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
              className="text-center"
            />
            <SortableTableHead
              label="Updated"
              sortKey="updated"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
              className="text-center"
            />
            <SortableTableHead
              label="Action type"
              sortKey="actionType"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <SortableTableHead
              label="Error message"
              sortKey="errorMessage"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <SortableTableHead
              label="Error details"
              sortKey="errorDetails"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <TableHead className="w-12" />
          </TableRow>
          <TableRow className="hover:bg-transparent">
            {selectionMode && <TableHead className="w-10" />}
            {userActionColumns.map(({ key, placeholder }) => (
              <TableHead key={key} className="align-top pb-2 pt-0">
                <ColumnFilterInput
                  value={filters[key] ?? ""}
                  placeholder={placeholder}
                  onChange={(value) =>
                    setFilters((current) =>
                      setColumnFilter(current, key, value),
                    )
                  }
                />
              </TableHead>
            ))}
            <TableHead className="w-12" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {displayRows.length === 0 ? (
            <TableRow>
              <TableCell
                colSpan={columnCount}
                className="text-center text-sm text-muted-foreground py-8"
              >
                No rows match filters.
              </TableCell>
            </TableRow>
          ) : (
            displayRows.map((row) => (
              <TableRow key={row.id}>
                {selectionMode && selectedIds && onToggleRow && (
                  <TableSelectionCell
                    rowId={row.id}
                    selected={selectedIds.has(row.id)}
                    onToggleRow={onToggleRow}
                  />
                )}
                <TableCell
                  className={debugTableCellClass("center", "font-mono text-xs")}
                >
                  <TruncatedTextWithTooltip
                    text={row.id}
                    maxLength={USER_ACTION_ID_DISPLAY_LENGTH}
                  />
                </TableCell>
                <TableCell className={debugTableCellClass("center")}>
                  <CenteredCellContent>
                    <DebugStatusCell status={row.status} />
                  </CenteredCellContent>
                </TableCell>
                <TableCell className={debugTableCellClass("center")}>
                  {formatDateTime(getUserActionUpdatedAt(row))}
                </TableCell>
                <TableCell className={debugTableCellClass("left")}>
                  {getConfigurationActionType(row.configuration)}
                </TableCell>
                <TableCell className={debugTableCellClass("left")}>
                  {getUserActionResultErrorMessage(row.result)}
                </TableCell>
                <TableCell
                  className={debugTableCellClass("left", "font-mono text-xs")}
                >
                  <TruncatedTextWithTooltip
                    text={getUserActionResultErrorDetails(row.result)}
                  />
                </TableCell>
                <TableCell>
                  <button
                    type="button"
                    className="text-muted-foreground hover:text-foreground"
                    aria-label="View JSON"
                    onClick={() => setDetail(row)}
                  >
                    <Eye className="size-4" />
                  </button>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
      <JsonDetailDialog
        title="User action"
        data={detail}
        open={detail !== null}
        onOpenChange={(open) => {
          if (!open) setDetail(null)
        }}
      />
    </>
  )
}
