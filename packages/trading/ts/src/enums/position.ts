// Mirrors octobot_trading/enums.py position enums

export const PositionSide = {
  LONG: "long",
  SHORT: "short",
  BOTH: "both",
  UNKNOWN: "unknown",
} as const
export type PositionSideValue = (typeof PositionSide)[keyof typeof PositionSide]

export const PositionStatus = {
  LIQUIDATING: "liquidating",
  LIQUIDATED: "liquidated",
  OPEN: "open",
  ADL: "auto_deleveraging",
} as const
export type PositionStatusValue = (typeof PositionStatus)[keyof typeof PositionStatus]
