import { Eye, X, Zap } from "lucide-react"
import { useMemo, useState } from "react"

import type { AccountTradingWithAccountId, AutomationState } from "@/client"
import { CenteredCellContent } from "@/components/Common/Tables/CenteredCellContent"
import { ClearTableFiltersButton } from "@/components/Common/Tables/ClearTableFiltersButton"
import { ColumnFilterInput } from "@/components/Common/Tables/ColumnFilterInput"
import { CopyableIdCell } from "@/components/Common/Tables/CopyableIdCell"
import { SortableTableHead } from "@/components/Common/Tables/SortableTableHead"
import { TableSelectionCell } from "@/components/Common/Tables/TableSelectionCell"
import { TableSelectionHeader } from "@/components/Common/Tables/TableSelectionHeader"
import { TruncatedTextWithTooltip } from "@/components/Common/Tables/TruncatedTextWithTooltip"
import { AssetsPortfolioCell } from "@/components/Debug/cells/AssetsPortfolioCell"
import { AutomationTradingCountCell } from "@/components/Debug/cells/AutomationTradingCountCell"
import { DebugStatusCell } from "@/components/Debug/cells/DebugStatusCell"
import { JsonDetailDialog } from "@/components/Debug/dialogs/JsonDetailDialog"
import { SignalAutomationDialog } from "@/components/Debug/dialogs/SignalAutomationDialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  formatActionProgress,
  getAutomationErrorTooltipLines,
  getAutomationUpdatedAt,
  isRunningAutomation,
} from "@/lib/debug/automation"
import {
  AUTOMATION_ASSETS_MAX_VISIBLE,
  AUTOMATION_COMPACT_COLUMN_CLASS,
  AUTOMATION_NAME_DISPLAY_LENGTH,
  AUTOMATION_TABLE_DEFAULT_SORT,
  LATEST_ACTION_DISPLAY_LENGTH,
} from "@/lib/debug/constants"
import {
  debugTableCellClass,
  getAutomationOrdersTooltipContent,
  getAutomationTradesTooltipContent,
} from "@/lib/debug/display-utils"
import { getAutomationDslHint } from "@/lib/debug/dsl"
import {
  automationFilterHeadClass,
  filterAutomations,
  sortAutomations,
} from "@/lib/debug/table-automations"
import type { AutomationSortKey } from "@/lib/debug/types"
import { formatDateTime } from "@/lib/format-datetime"
import { hasActiveFilters, setColumnFilter, toggleSort } from "@/lib/table"
import type { ColumnFilters, SortState } from "@/lib/table-types"
import { cn } from "@/lib/utils"

type AutomationsTableProps = {
  rows: AutomationState[]
  walletAddress?: string
  accountTradings: AccountTradingWithAccountId[]
  onSuccess?: () => void
  onStop?: (automation: AutomationState) => void
  onSignal?: (automation: AutomationState) => void
  readOnly?: boolean
  selectionMode?: boolean
  selectedIds?: Set<string>
  onToggleRow?: (id: string) => void
  onToggleAllVisible?: (ids: string[], select: boolean) => void
}

export function AutomationsTable({
  rows,
  walletAddress,
  accountTradings,
  onSuccess,
  onStop,
  onSignal,
  readOnly = false,
  selectionMode = false,
  selectedIds,
  onToggleRow,
  onToggleAllVisible,
}: AutomationsTableProps) {
  const [detail, setDetail] = useState<AutomationState | null>(null)
  const [signalTarget, setSignalTarget] = useState<AutomationState | null>(null)
  const [sort, setSort] = useState<SortState<AutomationSortKey>>(
    AUTOMATION_TABLE_DEFAULT_SORT,
  )
  const [filters, setFilters] = useState<ColumnFilters<AutomationSortKey>>({})

  const displayRows = useMemo(
    () => sortAutomations(filterAutomations(rows, filters), sort),
    [rows, sort, filters],
  )

  const automationColumns: AutomationSortKey[] = [
    "id",
    "status",
    "updated",
    "name",
    "progress",
    "dsl",
    "exchanges",
    "assets",
    "orders",
    "trades",
  ]

  const automationColumnCount = automationColumns.length + 1 + (selectionMode ? 1 : 0)
  const actionsHeadClass = "w-32"
  const visibleRowIds = useMemo(
    () => displayRows.map((row) => row.id),
    [displayRows],
  )

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        No automations.
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
              label="Name"
              sortKey="name"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <SortableTableHead
              label="Actions"
              sortKey="progress"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
              className={cn(AUTOMATION_COMPACT_COLUMN_CLASS, "text-center")}
            />
            <SortableTableHead
              label="Latest action"
              sortKey="dsl"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
            />
            <SortableTableHead
              label="Exchange"
              sortKey="exchanges"
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
              className={cn(AUTOMATION_COMPACT_COLUMN_CLASS, "text-center")}
            />
            <SortableTableHead
              label="Trds"
              sortKey="trades"
              sort={sort}
              onSort={(key) => setSort((current) => toggleSort(current, key))}
              className={cn(AUTOMATION_COMPACT_COLUMN_CLASS, "text-center")}
            />
            <TableHead className={actionsHeadClass} />
          </TableRow>
          <TableRow className="hover:bg-transparent">
            {selectionMode && <TableHead className="w-10" />}
            {automationColumns.map((key) => (
              <TableHead key={key} className={automationFilterHeadClass(key)}>
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
                colSpan={automationColumnCount}
                className="text-center text-sm text-muted-foreground py-8"
              >
                No rows match filters.
              </TableCell>
            </TableRow>
          ) : (
            displayRows.map((row) => {
              const canSignal = readOnly
                ? Boolean(onSignal)
                : isRunningAutomation(row)
              const canStop = readOnly
                ? Boolean(onStop)
                : isRunningAutomation(row)
              const signalButton = (
                <button
                  type="button"
                  className={
                    canSignal
                      ? "text-muted-foreground hover:text-foreground"
                      : "text-muted-foreground/40 cursor-not-allowed"
                  }
                  aria-label={
                    readOnly ? "View signal user action" : "Send signal"
                  }
                  disabled={!canSignal}
                  onClick={() => {
                    if (!canSignal) return
                    if (readOnly && onSignal) {
                      onSignal(row)
                      return
                    }
                    setSignalTarget(row)
                  }}
                >
                  <Zap className="size-4" />
                </button>
              )
              return (
                <TableRow key={row.id}>
                  {selectionMode && selectedIds && onToggleRow && (
                    <TableSelectionCell
                      rowId={row.id}
                      selected={selectedIds.has(row.id)}
                      onToggleRow={onToggleRow}
                    />
                  )}
                  <TableCell className={debugTableCellClass("center")}>
                    <CenteredCellContent>
                      <CopyableIdCell id={row.id} />
                    </CenteredCellContent>
                  </TableCell>
                  <TableCell className={debugTableCellClass("center")}>
                    <CenteredCellContent>
                      <DebugStatusCell
                        status={row.status}
                        extraTooltipLines={getAutomationErrorTooltipLines(row)}
                        pulseWhenRunning
                      />
                    </CenteredCellContent>
                  </TableCell>
                  <TableCell className={debugTableCellClass("center")}>
                    {formatDateTime(getAutomationUpdatedAt(row))}
                  </TableCell>
                  <TableCell className={debugTableCellClass("left")}>
                    <TruncatedTextWithTooltip
                      text={row.metadata.name}
                      maxLength={AUTOMATION_NAME_DISPLAY_LENGTH}
                    />
                  </TableCell>
                  <TableCell
                    className={debugTableCellClass(
                      "center",
                      `font-mono text-xs ${AUTOMATION_COMPACT_COLUMN_CLASS}`,
                    )}
                  >
                    {formatActionProgress(row)}
                  </TableCell>
                  <TableCell
                    className={debugTableCellClass("left", "font-mono text-xs")}
                  >
                    <TruncatedTextWithTooltip
                      text={getAutomationDslHint(row)}
                      maxLength={LATEST_ACTION_DISPLAY_LENGTH}
                    />
                  </TableCell>
                  <TableCell className={debugTableCellClass("left")}>
                    {row.exchanges?.length ? row.exchanges.join(", ") : "—"}
                  </TableCell>
                  <TableCell
                    className={debugTableCellClass("left", "font-mono text-xs")}
                  >
                    <AssetsPortfolioCell
                      assets={row.assets}
                      maxVisible={AUTOMATION_ASSETS_MAX_VISIBLE}
                    />
                  </TableCell>
                  <TableCell
                    className={debugTableCellClass(
                      "center",
                      `font-mono text-xs ${AUTOMATION_COMPACT_COLUMN_CLASS}`,
                    )}
                  >
                    <AutomationTradingCountCell
                      count={row.orders?.length ?? 0}
                      tooltip={getAutomationOrdersTooltipContent(
                        row,
                        accountTradings,
                      )}
                    />
                  </TableCell>
                  <TableCell
                    className={debugTableCellClass(
                      "center",
                      `font-mono text-xs ${AUTOMATION_COMPACT_COLUMN_CLASS}`,
                    )}
                  >
                    <AutomationTradingCountCell
                      count={row.trades?.length ?? 0}
                      tooltip={getAutomationTradesTooltipContent(
                        row,
                        accountTradings,
                      )}
                    />
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
                      {canSignal ? (
                        signalButton
                      ) : (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="inline-flex">{signalButton}</span>
                          </TooltipTrigger>
                          <TooltipContent side="left">
                            {readOnly
                              ? "Signal action unavailable"
                              : "Only running workflows can be signaled"}
                          </TooltipContent>
                        </Tooltip>
                      )}
                      {canStop ? (
                        <button
                          type="button"
                          className="text-muted-foreground hover:text-foreground"
                          aria-label={
                            readOnly
                              ? "View stop user action"
                              : "Stop automation"
                          }
                          onClick={() => onStop?.(row)}
                        >
                          <X className="size-4" />
                        </button>
                      ) : (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="inline-flex">
                              <button
                                type="button"
                                className="text-muted-foreground/40 cursor-not-allowed"
                                aria-label="Stop automation"
                                disabled
                              >
                                <X className="size-4" />
                              </button>
                            </span>
                          </TooltipTrigger>
                          <TooltipContent side="left">
                            {readOnly
                              ? "Stop action unavailable"
                              : "Only running automations can be stopped"}
                          </TooltipContent>
                        </Tooltip>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              )
            })
          )}
        </TableBody>
      </Table>
      <JsonDetailDialog
        title="Automation"
        data={detail}
        open={detail !== null}
        onOpenChange={(open) => {
          if (!open) setDetail(null)
        }}
      />
      {!readOnly && (
        <SignalAutomationDialog
          automation={signalTarget}
          open={signalTarget !== null}
          onOpenChange={(open) => {
            if (!open) setSignalTarget(null)
          }}
          walletAddress={walletAddress}
          onSuccess={onSuccess ?? (() => {})}
        />
      )}
    </>
  )
}
