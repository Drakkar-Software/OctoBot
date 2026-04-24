import {
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
  type VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table"
import { ArrowLeft, ArrowUpDown, Download, Eye, EyeOff, Loader2, Plus, Search, Upload, X } from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import type { Task_Output as Task } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { generateCSV, downloadCSV } from "@/lib/csv"
import {
  EXPORT_TEMPLATES,
  getAllExportTemplates,
  validateExportTemplateJson,
  saveUserExportTemplate,
  type ExportColumnDef,
} from "@/lib/export-templates"
import useCustomToast from "@/hooks/useCustomToast"
import { decryptAndVerify, type ClientKeys } from "@/lib/client-encryption"
import {
  extractValue,
  discoverPaths,
  formatCellValue,
} from "@/lib/json-path"
import { loadClientKeys } from "@/lib/device-key"
import { fetchServerPublicKeys } from "@/lib/server-keys"
import { getActiveExecution } from "@/utils/executions"

// ── Types ──────────────────────────────────────────────────────────────

interface ExportRow {
  taskId: string
  /** Parsed result JSON */
  resultData: Record<string, unknown>
  /** Task-level metadata injected as special keys */
  meta: Record<string, unknown>
}

export interface ExportResultsContentProps {
  tasks: Task[]
  onClose?: () => void
}

// ── Helpers ────────────────────────────────────────────────────────────

/** Resolve a column's jsonPath against a row, checking meta keys first. */
function resolveValue(
  row: ExportRow,
  jsonPath: string,
): unknown {
  if (jsonPath.startsWith("__") && jsonPath.endsWith("__")) {
    return row.meta[jsonPath]
  }
  return extractValue(row.resultData, jsonPath)
}

function buildExportRows(tasks: Task[]): ExportRow[] {
  return tasks
    .map((task) => {
      const activeExec = getActiveExecution(task.executions)
      let resultData: Record<string, unknown> = {}
      try {
        const parsed = activeExec?.result ? JSON.parse(activeExec.result) : {}
        resultData =
          typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)
            ? parsed
            : { result: parsed }
      } catch {
        resultData = { result: activeExec?.result ?? "" }
      }

      return {
        taskId: task.id ?? "",
        resultData,
        meta: {
          __task_name__: task.name ?? "",
          __exec_status__: activeExec?.status ?? "",
          __task_status__: task.error ? "errored" : (activeExec?.status ?? ""),
          __task_error__: task.error ?? "",
          __exec_type__: activeExec?.type ?? "",
          __exec_completed_at__: activeExec?.completed_at ?? "",
          __exec_result_metadata__: activeExec?.result_metadata ?? "",
        },
      }
    })
}

function buildColumnsForFullDetails(
  rows: ExportRow[],
): ExportColumnDef[] {
  // Discover all paths across all rows
  const allPaths = new Set<string>()
  for (const row of rows) {
    for (const path of discoverPaths(row.resultData)) {
      allPaths.add(path)
    }
  }

  const metaCols: ExportColumnDef[] = [
    { key: "name", label: "Name", jsonPath: "__task_name__" },
    { key: "status", label: "Status", jsonPath: "__exec_status__" },
  ]

  const dataCols: ExportColumnDef[] = Array.from(allPaths)
    .sort()
    .map((path) => ({
      key: `data_${path}`,
      label: path,
      jsonPath: path,
    }))

  return [...metaCols, ...dataCols]
}

// ── Component ──────────────────────────────────────────────────────────

export default function ExportResultsContent({
  tasks,
  onClose,
}: ExportResultsContentProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [userTemplatesVersion, setUserTemplatesVersion] = useState(0)
  const [selectedTemplateId, setSelectedTemplateId] = useState("general")
  const [customColumns, setCustomColumns] = useState<ExportColumnDef[]>([])
  const [addColumnPath, setAddColumnPath] = useState("")
  const [addColumnLabel, setAddColumnLabel] = useState("")
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [globalFilter, setGlobalFilter] = useState("")

  const exportRows = useMemo(() => buildExportRows(tasks), [tasks])
  const [decryptedRows, setDecryptedRows] = useState<ExportRow[] | null>(null)
  const [isDecrypting, setIsDecrypting] = useState(false)

  const showErrorToastRef = useRef(showErrorToast)
  showErrorToastRef.current = showErrorToast

  const encryptedTaskCount = useMemo(
    () => tasks.filter((t) => getActiveExecution(t.executions)?.result_metadata).length,
    [tasks],
  )

  useEffect(() => {
    let cancelled = false
    async function tryDecryptAll() {
      const rawKeys = await loadClientKeys()
      if (!rawKeys?.rsa_private?.trim()) return
      const keys = rawKeys as ClientKeys
      let serverKeys: { rsa_public: string; ecdsa_public: string }
      try {
        serverKeys = await fetchServerPublicKeys()
      } catch {
        showErrorToastRef.current("Failed to fetch server keys — encrypted results cannot be decrypted")
        return
      }
      if (cancelled) return
      setDecryptedRows(null)
      setIsDecrypting(true)
      let failCount = 0
      try {
        const base = buildExportRows(tasks)
        const rows = await Promise.all(
          tasks.map(async (task, i) => {
            const activeExec = getActiveExecution(task.executions)
            if (!activeExec?.result_metadata || !activeExec?.result) return base[i]
            try {
              const decrypted = await decryptAndVerify(activeExec.result, activeExec.result_metadata, keys, serverKeys.ecdsa_public)
              let resultData: Record<string, unknown> = {}
              try {
                const parsed: unknown = JSON.parse(decrypted)
                resultData =
                  typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)
                    ? (parsed as Record<string, unknown>)
                    : { result: parsed }
              } catch {
                resultData = { result: decrypted }
              }
              return { ...base[i], resultData }
            } catch {
              failCount++
              return base[i]
            }
          }),
        )
        if (!cancelled) {
          setDecryptedRows(rows)
          if (failCount > 0) showErrorToastRef.current(`Failed to decrypt ${failCount} result(s) — check your keys`)
        }
      } finally {
        if (!cancelled) setIsDecrypting(false)
      }
    }
    tryDecryptAll()
    return () => { cancelled = true }
  }, [tasks])

  const displayRows = decryptedRows ?? exportRows

  const discoveredPaths = useMemo(() => {
    const paths = new Set<string>()
    for (const row of displayRows) {
      for (const path of discoverPaths(row.resultData)) {
        paths.add(path)
      }
    }
    return Array.from(paths).sort()
  }, [displayRows])

  const activeTemplate = useMemo(
    () => getAllExportTemplates().find((t) => t.id === selectedTemplateId),
    [selectedTemplateId, userTemplatesVersion],
  )

  const templateColumns = useMemo((): ExportColumnDef[] => {
    if (selectedTemplateId === "full") {
      return buildColumnsForFullDetails(displayRows)
    }
    return activeTemplate?.columns ?? []
  }, [activeTemplate, selectedTemplateId, displayRows])

  const allColumns = useMemo(
    () => [...templateColumns, ...customColumns],
    [templateColumns, customColumns],
  )

  const tableColumns = useMemo((): ColumnDef<ExportRow>[] => {
    return allColumns.map((col) => ({
      id: col.key,
      accessorFn: (row: ExportRow) => {
        const val = resolveValue(row, col.jsonPath)
        return formatCellValue(val, col.formatter)
      },
      header: ({ column }) => (
        <Button
          variant="ghost"
          size="sm"
          className="-ml-3 h-8"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          {col.label}
          {col.isCustom && (
            <Badge variant="secondary" className="ml-1 text-[10px] px-1 py-0">
              custom
            </Badge>
          )}
          <ArrowUpDown className="ml-1 size-3" />
        </Button>
      ),
      cell: ({ getValue }) => (
        <span className="max-w-[300px] truncate block text-xs">
          {String(getValue() ?? "")}
        </span>
      ),
      enableColumnFilter: true,
      filterFn: "includesString",
    }))
  }, [allColumns])

  const table = useReactTable({
    data: displayRows,
    columns: tableColumns,
    state: { sorting, columnFilters, columnVisibility, globalFilter },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    globalFilterFn: "includesString",
  })

  const handleTemplateFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (!file) return
      e.target.value = ""
      try {
        const text = await file.text()
        const json: unknown = JSON.parse(text)
        const def = validateExportTemplateJson(json)
        saveUserExportTemplate(def)
        setUserTemplatesVersion((v) => v + 1)
        showSuccessToast(`Export template "${def.label}" imported`)
      } catch (err) {
        showErrorToast(err instanceof Error ? err.message : "Invalid template file")
      }
    },
    [showSuccessToast, showErrorToast],
  )

  const handleAddColumn = useCallback(() => {
    const path = addColumnPath.trim()
    const label = addColumnLabel.trim() || path
    if (!path) return

    setCustomColumns((prev) => [
      ...prev,
      {
        key: `custom_${Date.now()}`,
        label,
        jsonPath: path,
        isCustom: true,
      },
    ])
    setAddColumnPath("")
    setAddColumnLabel("")
  }, [addColumnPath, addColumnLabel])

  const handleRemoveCustomColumn = useCallback((key: string) => {
    setCustomColumns((prev) => prev.filter((c) => c.key !== key))
  }, [])

  const handleExport = useCallback(() => {
    const visibleRows = table.getFilteredRowModel().rows
    const headers = allColumns.map((c) => c.label)
    const csvRows = visibleRows.map((row) =>
      allColumns.map((col) => {
        const val = resolveValue(row.original, col.jsonPath)
        return formatCellValue(val, col.formatter)
      }),
    )
    const csv = generateCSV(headers, csvRows)
    downloadCSV(csv, `task-results-${new Date().toISOString().split("T")[0]}`)
    if (encryptedTaskCount > 0 && decryptedRows === null && !isDecrypting) {
      showErrorToast(`${encryptedTaskCount} encrypted result(s) exported as raw ciphertext — configure browser keys in Settings to decrypt`)
    } else {
      showSuccessToast(`Exported ${visibleRows.length} row(s)`)
    }
  }, [table, allColumns, encryptedTaskCount, decryptedRows, isDecrypting, showErrorToast, showSuccessToast])

  return (
    <div className="flex flex-col gap-3">
      {/* Controls row */}
      <div className="flex flex-wrap items-center gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          className="hidden"
          onChange={handleTemplateFileChange}
        />
        <Select
          value={selectedTemplateId}
          onValueChange={setSelectedTemplateId}
        >
          <SelectTrigger size="sm" className="w-44">
            <SelectValue placeholder="Template" />
          </SelectTrigger>
          <SelectContent>
            {getAllExportTemplates().map((t) => (
              <SelectItem key={t.id} value={t.id}>
                {t.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          variant="outline"
          size="sm"
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="size-3.5 mr-1" />
          Import Template
        </Button>

        <div className="relative flex items-center">
          <Search className="pointer-events-none absolute left-2.5 size-3.5 text-muted-foreground" />
          <Input
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder="Search all columns..."
            className="h-8 w-48 pl-8 text-xs"
          />
          {globalFilter && (
            <button
              onClick={() => setGlobalFilter("")}
              className="absolute right-2 text-muted-foreground hover:text-foreground"
            >
              <X className="size-3" />
            </button>
          )}
        </div>

        {/* Column visibility toggles */}
        <div className="flex gap-1 ml-auto">
          {allColumns.map((col) => {
            const isVisible =
              columnVisibility[col.key] !== false
            return (
              <Button
                key={col.key}
                variant="ghost"
                size="sm"
                className="h-6 px-1.5 text-[10px]"
                onClick={() =>
                  setColumnVisibility((prev) => ({
                    ...prev,
                    [col.key]: !isVisible,
                  }))
                }
              >
                {isVisible ? (
                  <Eye className="size-3 mr-0.5" />
                ) : (
                  <EyeOff className="size-3 mr-0.5" />
                )}
                {col.label.length > 12
                  ? `${col.label.slice(0, 12)}...`
                  : col.label}
              </Button>
            )
          })}
        </div>
      </div>

      {/* Add custom column */}
      <div className="flex items-center gap-2">
        <Input
          value={addColumnLabel}
          onChange={(e) => setAddColumnLabel(e.target.value)}
          placeholder="Column label"
          className="h-7 w-32 text-xs"
        />
        <Select
          value={addColumnPath}
          onValueChange={setAddColumnPath}
        >
          <SelectTrigger size="sm" className="w-48">
            <SelectValue placeholder="Select JSON path..." />
          </SelectTrigger>
          <SelectContent>
            {discoveredPaths.map((path) => (
              <SelectItem key={path} value={path}>
                {path}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          variant="outline"
          size="sm"
          onClick={handleAddColumn}
          disabled={!addColumnPath.trim()}
          className="h-7"
        >
          <Plus className="size-3 mr-1" /> Add Column
        </Button>

        {customColumns.length > 0 && (
          <div className="flex gap-1 ml-2">
            {customColumns.map((col) => (
              <Badge
                key={col.key}
                variant="secondary"
                className="text-xs cursor-pointer"
                onClick={() => handleRemoveCustomColumn(col.key)}
              >
                {col.label} <X className="size-2.5 ml-1" />
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Data table */}
      <div className="overflow-auto rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={tableColumns.length}
                  className="text-center text-muted-foreground py-8"
                >
                  No data to display
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <p className="text-xs text-muted-foreground flex items-center gap-1.5">
        {isDecrypting && <Loader2 className="size-3 animate-spin" />}
        {isDecrypting ? "Decrypting results…" : (
          <>Showing {table.getFilteredRowModel().rows.length} of {displayRows.length} rows</>
        )}
      </p>

      {/* Footer */}
      <div className="flex justify-between items-center pt-4 border-t">
        {onClose && (
          <Button variant="outline" onClick={onClose}>
            <ArrowLeft className="size-3.5 mr-1.5" />
            Back
          </Button>
        )}
        <Button onClick={handleExport} className={onClose ? "" : "ml-auto"}>
          <Download className="size-3.5 mr-1.5" />
          Download CSV ({table.getFilteredRowModel().rows.length} rows)
        </Button>
      </div>
    </div>
  )
}
