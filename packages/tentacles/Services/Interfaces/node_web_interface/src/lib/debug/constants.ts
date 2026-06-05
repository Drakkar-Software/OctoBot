import type { AutomationSignalType } from "@/client"
import type { AccountSortKey, AutomationSortKey } from "@/lib/debug/types"

export const SIGNAL_TYPE_OPTIONS: {
  value: AutomationSignalType
  label: string
}[] = [
  { value: "forced_trigger", label: "Forced trigger" },
  { value: "actions", label: "Actions" },
  { value: "trading_signal", label: "Trading signal" },
]

export const COMPOUND_DSL_KEYWORDS = new Set(["if_error", "loop_until", "value_if"])

export const ID_DISPLAY_LENGTH = 8
export const ERROR_DETAILS_DISPLAY_LENGTH = 35
export const LATEST_ACTION_DISPLAY_LENGTH = 22
export const AUTOMATION_NAME_DISPLAY_LENGTH = 20
export const USER_ACTION_ID_DISPLAY_LENGTH = 32

/** Short tooltips (assets, status errors): no overflow so Radix collision sizing does not force a scrollbar. */
export const COMPACT_TOOLTIP_CONTENT_CLASS =
  "font-mono text-xs text-left max-w-md whitespace-pre-line break-all p-3 [text-wrap:wrap]"

export const SCROLLABLE_TOOLTIP_INNER_CLASS =
  "max-h-[min(90vh,var(--radix-tooltip-content-available-height,90vh))] overflow-y-auto overflow-x-hidden whitespace-pre-wrap break-all p-3 font-mono text-xs text-left [text-wrap:wrap]"

export const AUTOMATION_ASSETS_MAX_VISIBLE = 2

export const AUTOMATION_COMPACT_COLUMN_CLASS = "w-0 px-2"

export const ACCOUNT_COMPACT_COLUMN_CLASS = "w-0 px-2"

export const AUTOMATION_COMPACT_COLUMNS = new Set<AutomationSortKey>([
  "progress",
  "orders",
  "trades",
])

export const ACCOUNT_COMPACT_COLUMNS = new Set<AccountSortKey>(["orders", "trades"])
