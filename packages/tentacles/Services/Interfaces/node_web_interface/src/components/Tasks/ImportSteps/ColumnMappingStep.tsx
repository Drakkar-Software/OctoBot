import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table"
import { Trash2 } from "lucide-react"
import { useCallback, useMemo, useRef, useState } from "react"

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
import useCustomToast from "@/hooks/useCustomToast"
import { type ActionParamDef, isParamValueValid } from "@/lib/action-templates"
import {
  buildParamValuesForRow,
  type ColumnMapping,
  detectColumnsAndTemplates,
  detectMappingsForTemplate,
} from "@/lib/column-detector"
import {
  getAllTemplates,
  getLastUsedImportTemplateId,
  getTemplateById,
  resolveMetaTemplate,
  saveUserMetaTemplate,
  setLastUsedImportTemplateId,
  validateMetaTemplateJson,
} from "@/lib/meta-templates"

const SENSITIVE_HEADER_PATTERNS =
  /\b(key|private|secret|password|mnemonic|seed|pk)\b/i

function isSensitiveHeader(header: string): boolean {
  return SENSITIVE_HEADER_PATTERNS.test(header)
}

// ── Types ──────────────────────────────────────────────────────────────

export interface ActionRow {
  rowIndex: number
  templateId: string
  paramValues: Record<string, string>
  mappings: ColumnMapping[]
  unmappedColumns: number[]
  /** User-provided task name (optional) */
  name: string
}

export interface ColumnMappingStepProps {
  headers: string[]
  rows: string[][]
  onConfirm: (actions: ActionRow[]) => void
  onBack: () => void
}

interface RowParamsCellProps {
  actionRow: ActionRow
  headers: string[]
  rows: string[][]
  onParamChange: (rowIndex: number, paramKey: string, value: string) => void
}

function RowParamsCell({
  actionRow,
  headers,
  rows,
  onParamChange,
}: RowParamsCellProps) {
  const { requiredParams, sortedOptional } = useMemo(() => {
    const template = getTemplateById(actionRow.templateId)
    const byLabel = (a: ActionParamDef, b: ActionParamDef) =>
      a.label.localeCompare(b.label)
    return {
      requiredParams: (
        template?.params.filter((p) => p.required && !p.hidden) ?? []
      ).sort(byLabel),
      sortedOptional: (
        template?.params.filter((p) => !p.required && !p.hidden) ?? []
      ).sort(byLabel),
    }
  }, [actionRow.templateId])

  const filledOptional = sortedOptional.filter((p) =>
    isParamValueValid(p, actionRow.paramValues[p.key]),
  )
  const emptyOptional = sortedOptional.filter(
    (p) => !isParamValueValid(p, actionRow.paramValues[p.key]),
  )

  const renderParam = (param: ActionParamDef) => {
    const value = actionRow.paramValues[param.key] ?? ""
    return (
      <div key={param.key} className="flex items-center gap-1">
        <span className="text-xs text-muted-foreground whitespace-nowrap">
          {param.label}
          {param.required && <span className="text-destructive">*</span>}:
        </span>
        <Input
          value={value}
          onChange={(e) =>
            onParamChange(actionRow.rowIndex, param.key, e.target.value)
          }
          type={
            param.type === "number"
              ? "number"
              : param.type === "password"
                ? "password"
                : "text"
          }
          placeholder={
            param.type === "numberOrDate"
              ? `${param.label} (number or date)`
              : param.label
          }
          className="h-6 text-xs w-28"
        />
      </div>
    )
  }

  return (
    <div className="space-y-1.5">
      <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-1.5">
        {requiredParams.map(renderParam)}
        {filledOptional.map(renderParam)}
      </div>
      {emptyOptional.length > 0 && (
        <details>
          <summary className="text-[10px] text-muted-foreground cursor-pointer">
            {emptyOptional.length} optional parameter
            {emptyOptional.length !== 1 ? "s" : ""}
          </summary>
          <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-1.5 mt-1.5">
            {emptyOptional.map(renderParam)}
          </div>
        </details>
      )}
      {actionRow.unmappedColumns.length > 0 && (
        <details>
          <summary className="text-[10px] text-muted-foreground cursor-pointer">
            {actionRow.unmappedColumns.length} unmapped column
            {actionRow.unmappedColumns.length !== 1 ? "s" : ""}
          </summary>
          <div className="flex flex-wrap gap-1 mt-1">
            {actionRow.unmappedColumns.map((colIdx) => {
              const header = headers[colIdx] ?? ""
              const value = rows[actionRow.rowIndex]?.[colIdx] ?? ""
              const masked = isSensitiveHeader(header)
              return (
                <span
                  key={colIdx}
                  className="text-[10px] bg-muted px-1.5 py-0.5 rounded"
                >
                  {header}:{" "}
                  {masked ? "\u2022\u2022\u2022\u2022\u2022\u2022" : value}
                </span>
              )
            })}
          </div>
        </details>
      )}
    </div>
  )
}

const columnHelper = createColumnHelper<ActionRow>()

export default function ColumnMappingStep({
  headers,
  rows,
  onConfirm,
  onBack,
}: ColumnMappingStepProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const fileInputRef = useRef<HTMLInputElement>(null)
  // Increment to force re-render after a user template is imported (getAllTemplates reads localStorage)
  const [, setUserTemplatesVersion] = useState(0)

  // Run initial detection
  const initialDetection = useMemo(
    () =>
      detectColumnsAndTemplates(
        headers,
        rows,
        getLastUsedImportTemplateId() ?? undefined,
      ),
    [headers, rows],
  )

  const [actionRows, setActionRows] = useState<ActionRow[]>(() => {
    const nameIdx = headers.findIndex((h) => h.trim().toLowerCase() === "name")
    return initialDetection.map((det, idx) => {
      const nameFromCsv =
        nameIdx >= 0 ? (rows[idx]?.[nameIdx] ?? "").trim() : ""
      const unmappedColumns =
        nameIdx >= 0 && det.unmappedColumns.includes(nameIdx)
          ? det.unmappedColumns.filter((i) => i !== nameIdx)
          : det.unmappedColumns
      return {
        rowIndex: idx,
        templateId: det.templateId,
        paramValues: det.paramValues,
        mappings: det.mappings,
        unmappedColumns,
        name: nameFromCsv || `Action ${idx + 1}`,
      }
    })
  })

  const updateRow = useCallback(
    (rowIndex: number, update: Partial<ActionRow>) => {
      setActionRows((prev) =>
        prev.map((row) =>
          row.rowIndex === rowIndex ? { ...row, ...update } : row,
        ),
      )
    },
    [],
  )

  const deleteRow = useCallback((rowIndex: number) => {
    setActionRows((prev) => prev.filter((row) => row.rowIndex !== rowIndex))
  }, [])

  const handleTemplateChange = useCallback(
    (rowIndex: number, newTemplateId: string) => {
      const template = getTemplateById(newTemplateId)
      if (!template) return

      const newMappings = detectMappingsForTemplate(template, headers, rows)
      const csvRow = rows[rowIndex]
      if (!csvRow) return

      const newParamValues = buildParamValuesForRow(
        csvRow,
        newMappings,
        template,
      )
      const mappedCols = new Set(newMappings.map((m) => m.columnIndex))
      const unmappedColumns = headers
        .map((_, i) => i)
        .filter((i) => !mappedCols.has(i))

      setLastUsedImportTemplateId(newTemplateId)
      updateRow(rowIndex, {
        templateId: newTemplateId,
        mappings: newMappings,
        paramValues: newParamValues,
        unmappedColumns,
      })
    },
    [headers, rows, updateRow],
  )

  const handleParamChange = useCallback(
    (rowIndex: number, paramKey: string, value: string) => {
      setActionRows((prev) =>
        prev.map((row) => {
          if (row.rowIndex !== rowIndex) return row
          return {
            ...row,
            paramValues: { ...row.paramValues, [paramKey]: value },
          }
        }),
      )
    },
    [],
  )

  const handleNameChange = useCallback(
    (rowIndex: number, name: string) => {
      updateRow(rowIndex, { name })
    },
    [updateRow],
  )

  const handleTemplateFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (!file) return
      e.target.value = ""
      try {
        const text = await file.text()
        const json: unknown = JSON.parse(text)
        const def = validateMetaTemplateJson(json)
        resolveMetaTemplate(def) // validate it resolves without errors
        saveUserMetaTemplate(def)
        setUserTemplatesVersion((v) => v + 1)
        showSuccessToast(`Template "${def.label}" imported`)
      } catch (err) {
        showErrorToast(
          err instanceof Error ? err.message : "Invalid template file",
        )
      }
    },
    [showSuccessToast, showErrorToast],
  )

  // Build dynamic columns based on the union of all param keys across rows
  const columns = useMemo(() => {
    const cols = [
      columnHelper.display({
        id: "row_number",
        header: "#",
        cell: (info) => (
          <span className="text-muted-foreground text-xs">
            {info.row.index + 1}
          </span>
        ),
        size: 40,
        maxSize: 40,
      }),
      columnHelper.accessor("name", {
        header: "Name",
        cell: (info) => (
          <Input
            value={info.getValue()}
            onChange={(e) =>
              handleNameChange(info.row.original.rowIndex, e.target.value)
            }
            className="h-7 text-xs w-32"
          />
        ),
        size: 140,
        maxSize: 140,
      }),
      columnHelper.accessor("templateId", {
        header: "Action Template",
        cell: (info) => (
          <Select
            value={info.getValue()}
            onValueChange={(val) =>
              handleTemplateChange(info.row.original.rowIndex, val)
            }
          >
            <SelectTrigger size="sm" className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {getAllTemplates().map((t) => (
                <SelectItem key={t.id} value={t.id}>
                  {t.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ),
        size: 160,
        maxSize: 160,
      }),
    ]

    return cols
  }, [handleNameChange, handleTemplateChange])

  const table = useReactTable({
    data: actionRows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium">
            {actionRows.length} action{actionRows.length !== 1 ? "s" : ""}{" "}
            detected
          </p>
          <p className="text-xs text-muted-foreground">
            Review auto-detected templates and parameter mappings. Edit values
            or change templates as needed.
          </p>
        </div>
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={handleTemplateFileChange}
          />
          <Button
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
          >
            Import Template
          </Button>
        </div>
      </div>

      <div className="max-h-[60vh] overflow-auto">
        <Table>
          <TableHeader>
            <TableRow>
              {table.getHeaderGroups().map((headerGroup) =>
                headerGroup.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    style={{ width: header.column.getSize() }}
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                  </TableHead>
                )),
              )}
              <TableHead>Parameters</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.map((row) => {
              const actionRow = row.original

              return (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell
                      key={cell.id}
                      style={{ width: cell.column.getSize() }}
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </TableCell>
                  ))}
                  <TableCell>
                    <RowParamsCell
                      actionRow={actionRow}
                      headers={headers}
                      rows={rows}
                      onParamChange={handleParamChange}
                    />
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteRow(actionRow.rowIndex)}
                      className="h-6 w-6 p-0"
                    >
                      <Trash2 className="size-3.5 text-destructive" />
                    </Button>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>

      <div className="flex gap-2 justify-end">
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>
        <Button
          onClick={() => onConfirm(actionRows)}
          disabled={actionRows.length === 0}
        >
          Review {actionRows.length} Action
          {actionRows.length !== 1 ? "s" : ""}
        </Button>
      </div>
    </div>
  )
}
