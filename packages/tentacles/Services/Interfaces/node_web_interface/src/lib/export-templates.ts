/**
 * Export templates define how bot result JSON is mapped to table columns.
 * Pre-defined templates cover common use cases; users can also add custom columns.
 */

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

export const TRADE_EXPORT_TEMPLATE: ExportTemplate = {
  id: "trade",
  label: "Trade Results",
  description: "Trading execution details: symbol, side, amount, price",
  columns: [
    { key: "name", label: "Name", jsonPath: "__task_name__", formatter: "text" },
    { key: "status", label: "Status", jsonPath: "__exec_status__", formatter: "text" },
    { key: "symbol", label: "Symbol", jsonPath: "symbol", formatter: "text" },
    { key: "side", label: "Side", jsonPath: "side", formatter: "text" },
    { key: "amount", label: "Amount", jsonPath: "amount", formatter: "number" },
    { key: "price", label: "Price", jsonPath: "price", formatter: "number" },
    { key: "exchange", label: "Exchange", jsonPath: "exchange", formatter: "text" },
    { key: "order_id", label: "Order ID", jsonPath: "order_id", formatter: "text" },
  ],
}

export const TRANSFER_EXPORT_TEMPLATE: ExportTemplate = {
  id: "transfer",
  label: "Transfer Results",
  description: "Blockchain transfer details: addresses, amounts, tx hash",
  columns: [
    { key: "name", label: "Name", jsonPath: "__task_name__", formatter: "text" },
    { key: "status", label: "Status", jsonPath: "__exec_status__", formatter: "text" },
    { key: "from_address", label: "From Address", jsonPath: "from_address", formatter: "text" },
    { key: "to_address", label: "To Address", jsonPath: "to_address", formatter: "text" },
    { key: "amount", label: "Amount", jsonPath: "amount", formatter: "number" },
    { key: "asset", label: "Asset", jsonPath: "asset", formatter: "text" },
    { key: "tx_hash", label: "TX Hash", jsonPath: "tx_hash", formatter: "text" },
    { key: "network", label: "Network", jsonPath: "network", formatter: "text" },
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
  return EXPORT_TEMPLATES.find((t) => t.id === id)
}
