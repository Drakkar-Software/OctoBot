// Mirrors octobot_trading/enums.py exchange type enums

export const ExchangeTypes = {
  SPOT: "spot",
  FUTURE: "future",
  MARGIN: "margin",
  SWAP: "swap",
  OPTION: "option",
  UNKNOWN: "unknown",
} as const
export type ExchangeTypeValue = (typeof ExchangeTypes)[keyof typeof ExchangeTypes]

export const ExchangeSupportedElements = {
  UNSUPPORTED_ORDERS: "unsupported_orders",
  SUPPORTED_BUNDLED_ORDERS: "supported_bundled_orders",
} as const

export const AccountTypes = {
  CASH: "cash",
  MARGIN: "margin",
  FUTURE: "future",
  SWAP: "swap",
  OPTION: "option",
} as const
export type AccountTypeValue = (typeof AccountTypes)[keyof typeof AccountTypes]

export const PositionMode = {
  HEDGE: "hedge_mode",
  ONE_WAY: "one_way_mode",
} as const
export type PositionModeValue = (typeof PositionMode)[keyof typeof PositionMode]

export const MarginType = {
  ISOLATED: "isolated",
  CROSS: "cross",
} as const
export type MarginTypeValue = (typeof MarginType)[keyof typeof MarginType]
