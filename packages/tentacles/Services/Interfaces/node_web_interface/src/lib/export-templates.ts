/**
 * Export templates define how bot result JSON is mapped to table columns.
 * Pre-defined templates cover common use cases; users can also add custom columns.
 */

import { z } from "zod"

export type ColumnFormatter = "date" | "number" | "json" | "text"

export interface ExportColumnDef {
  key: string
  label: string
  jsonPath: string
  formatter?: ColumnFormatter
  /** Whether this column was added by the user (not from a pre-defined template) */
  isCustom?: boolean
}

export interface ExportTemplate {
  id: string
  label: string
  description: string
  columns: ExportColumnDef[]
}

export const GENERAL_EXPORT_TEMPLATE: ExportTemplate = {
  id: "general",
  label: "General",
  description: "Basic task info: name, status, execution date, and errors",
  columns: [
    { key: "name", label: "Name", jsonPath: "__task_name__", formatter: "text" },
    { key: "status", label: "Status", jsonPath: "__task_status__", formatter: "text" },
    { key: "exec_type", label: "Execution Type", jsonPath: "__exec_type__", formatter: "text" },
    { key: "completed_at", label: "Completed At", jsonPath: "__exec_completed_at__", formatter: "date" },
    { key: "error", label: "Error", jsonPath: "__task_error__", formatter: "text" },
  ],
}

const TRADE_STATE_PREFIX = "state.automation.client_exchange_account_elements.trades[0]"

export const TRADE_EXPORT_TEMPLATE: ExportTemplate = {
  id: "trade",
  label: "Trade Results",
  description: "Exchange trade details",
  columns: [
    { key: "name", label: "Name", jsonPath: "__task_name__", formatter: "text" },
    { key: "status", label: "Status", jsonPath: "__exec_status__", formatter: "text" },
    { key: "timestamp", label: "Timestamp", jsonPath: `${TRADE_STATE_PREFIX}.timestamp`, formatter: "date" },
    { key: "symbol", label: "Symbol", jsonPath: `${TRADE_STATE_PREFIX}.symbol`, formatter: "text" },
    { key: "type", label: "Type", jsonPath: `${TRADE_STATE_PREFIX}.type`, formatter: "text" },
    { key: "side", label: "Side", jsonPath: `${TRADE_STATE_PREFIX}.side`, formatter: "text" },
    { key: "amount", label: "Amount", jsonPath: `${TRADE_STATE_PREFIX}.amount`, formatter: "number" },
    { key: "price", label: "Price", jsonPath: `${TRADE_STATE_PREFIX}.price`, formatter: "number" },
    { key: "cost", label: "Cost", jsonPath: `${TRADE_STATE_PREFIX}.cost`, formatter: "number" },
    { key: "creation_time", label: "Creation Time", jsonPath: `${TRADE_STATE_PREFIX}.creation_time`, formatter: "date" },
    { key: "entries", label: "Entries", jsonPath: `${TRADE_STATE_PREFIX}.entries`, formatter: "json" },
    { key: "exchange_id", label: "Exchange ID", jsonPath: `${TRADE_STATE_PREFIX}.exchange_id`, formatter: "text" },
    { key: "exchange_trade_id", label: "Exchange Trade ID", jsonPath: `${TRADE_STATE_PREFIX}.exchange_trade_id`, formatter: "text" },
    { key: "fee_cost", label: "Fee Cost", jsonPath: `${TRADE_STATE_PREFIX}.fee.cost`, formatter: "number" },
    { key: "fee_currency", label: "Fee Currency", jsonPath: `${TRADE_STATE_PREFIX}.fee.currency`, formatter: "text" },
    { key: "quantity_currency", label: "Quantity Currency", jsonPath: `${TRADE_STATE_PREFIX}.quantity_currency`, formatter: "text" },
    { key: "reduce_only", label: "Reduce Only", jsonPath: `${TRADE_STATE_PREFIX}.reduceOnly`, formatter: "text" },
    { key: "trade_status", label: "Trade Status", jsonPath: `${TRADE_STATE_PREFIX}.status`, formatter: "text" },
    { key: "tag", label: "Tag", jsonPath: `${TRADE_STATE_PREFIX}.tag`, formatter: "text" },
  ],
}

const AUTOMATION_STATE_PREFIX = "state.automation.client_exchange_account_elements.transactions[0]"

export const TRANSFER_EXPORT_TEMPLATE: ExportTemplate = {
  id: "transfer",
  label: "Transfer Results",
  description: "Blockchain transfer details",
  columns: [
    { key: "name", label: "Name", jsonPath: "__task_name__", formatter: "text" },
    { key: "status", label: "Status", jsonPath: "__exec_status__", formatter: "text" },
    { key: "address_from", label: "From Address", jsonPath: `${AUTOMATION_STATE_PREFIX}.address_from`, formatter: "text" },
    { key: "address_to", label: "To Address", jsonPath: `${AUTOMATION_STATE_PREFIX}.address_to`, formatter: "text" },
    { key: "amount", label: "Amount", jsonPath: `${AUTOMATION_STATE_PREFIX}.amount`, formatter: "number" },
    { key: "currency", label: "Currency", jsonPath: `${AUTOMATION_STATE_PREFIX}.currency`, formatter: "text" },
    { key: "txid", label: "TX Id", jsonPath: `${AUTOMATION_STATE_PREFIX}.txid`, formatter: "text" },
    { key: "fee_cost", label: "Fee Cost", jsonPath: `${AUTOMATION_STATE_PREFIX}.fee.cost`, formatter: "number" },
    { key: "fee_currency", label: "Fee Currency", jsonPath: `${AUTOMATION_STATE_PREFIX}.fee.currency`, formatter: "text" },
    { key: "timestamp", label: "Time", jsonPath: `${AUTOMATION_STATE_PREFIX}.timestamp`, formatter: "date" },
    { key: "network", label: "Network", jsonPath: `${AUTOMATION_STATE_PREFIX}.network`, formatter: "text" },
  ],
}

export const FULL_DETAILS_TEMPLATE: ExportTemplate = {
  id: "full",
  label: "Full Details",
  description: "All available fields auto-discovered from the result data",
  columns: [], // Populated dynamically from result JSON
}

export const EXPORT_TEMPLATES: ExportTemplate[] = [
  GENERAL_EXPORT_TEMPLATE,
  TRADE_EXPORT_TEMPLATE,
  TRANSFER_EXPORT_TEMPLATE,
  FULL_DETAILS_TEMPLATE,
]

export function getExportTemplateById(id: string): ExportTemplate | undefined {
  return getAllExportTemplates().find((t) => t.id === id)
}

const ExportColumnDefSchema = z.object({
  key: z.string().min(1),
  label: z.string().min(1),
  jsonPath: z.string().min(1),
  formatter: z.enum(["date", "number", "json", "text"]).optional(),
})

const ExportTemplateDefSchema = z.object({
  id: z.string().min(1),
  label: z.string().min(1),
  description: z.string(),
  columns: z.array(ExportColumnDefSchema),
})

export function validateExportTemplateJson(json: unknown): ExportTemplate {
  return ExportTemplateDefSchema.parse(json)
}

const STORAGE_KEY = "user_export_templates"

const RESERVED_IDS: ReadonlySet<string> = new Set(
  EXPORT_TEMPLATES.map((t) => t.id),
)

export function loadUserExportTemplates(): ExportTemplate[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.flatMap((item) => {
      const result = ExportTemplateDefSchema.safeParse(item)
      return result.success ? [result.data] : []
    })
  } catch {
    return []
  }
}

export function saveUserExportTemplate(def: ExportTemplate): void {
  if (RESERVED_IDS.has(def.id)) {
    throw new Error(
      `Template ID "${def.id}" is reserved and cannot be used for user templates`,
    )
  }
  const existing = loadUserExportTemplates()
  const updated = existing.filter((t) => t.id !== def.id)
  updated.push(def)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
}

export function deleteUserExportTemplate(id: string): void {
  const existing = loadUserExportTemplates()
  const updated = existing.filter((t) => t.id !== id)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
}

export function getAllExportTemplates(): ExportTemplate[] {
  return [...EXPORT_TEMPLATES, ...loadUserExportTemplates()]
}
