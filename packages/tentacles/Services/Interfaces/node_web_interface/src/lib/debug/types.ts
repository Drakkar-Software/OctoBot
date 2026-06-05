import type { UserActionType } from "@/client"

export type ExecuteActionDraft = {
  actionType: UserActionType
  jsonText: string
}

export type AutomationSortKey =
  | "id"
  | "status"
  | "name"
  | "progress"
  | "dsl"
  | "trades"
  | "exchanges"
  | "assets"
  | "orders"
  | "updated"

export type UserActionSortKey =
  | "id"
  | "status"
  | "actionType"
  | "updated"
  | "errorMessage"
  | "errorDetails"

export type AccountSortKey =
  | "id"
  | "authenticationId"
  | "name"
  | "updated"
  | "stateStatus"
  | "stateMessage"
  | "assets"
  | "orders"
  | "trades"
  | "simulated"
  | "exchange"

export type ExchangeConfigSortKey =
  | "id"
  | "exchange"
  | "name"
  | "accounts"
  | "sandboxed"
  | "url"

export type StrategySortKey =
  | "id"
  | "name"
  | "version"
  | "updated"
  | "description"
  | "referenceMarket"
  | "configType"
