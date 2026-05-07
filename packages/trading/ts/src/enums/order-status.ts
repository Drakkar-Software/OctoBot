// Mirrors octobot_trading/enums.py order/trade enums

export const OrderStatus = {
  PENDING_CREATION: "pending_creation",
  OPEN: "open",
  PARTIALLY_FILLED: "partially_filled",
  FILLED: "filled",
  CANCELED: "canceled",
  PENDING_CANCEL: "canceling",
  CLOSED: "closed",
  EXPIRED: "expired",
  REJECTED: "rejected",
  UNKNOWN: "unknown",
} as const
export type OrderStatusValue = (typeof OrderStatus)[keyof typeof OrderStatus]

export const TradeOrderSide = {
  BUY: "buy",
  SELL: "sell",
} as const
export type TradeOrderSideValue = (typeof TradeOrderSide)[keyof typeof TradeOrderSide]

export const TradeOrderType = {
  LIMIT: "limit",
  MARKET: "market",
  STOP_LOSS: "stop_loss",
  STOP_LOSS_LIMIT: "stop_loss_limit",
  CONDITIONAL_MARKET: "stop_market",
  CONDITIONAL_LIMIT: "stop_limit",
  TAKE_PROFIT: "take_profit",
  TAKE_PROFIT_LIMIT: "take_profit_limit",
  TRAILING_STOP: "trailing_stop",
  TRAILING_STOP_LIMIT: "trailing_stop_limit",
  LIMIT_MAKER: "limit_maker",
  UNSUPPORTED: "unsupported",
  UNKNOWN: "unknown",
} as const
export type TradeOrderTypeValue = (typeof TradeOrderType)[keyof typeof TradeOrderType]

export const TraderOrderType = {
  BUY_MARKET: "buy_market",
  BUY_LIMIT: "buy_limit",
  STOP_LOSS: "stop_loss",
  STOP_LOSS_LIMIT: "stop_limit",
  SELL_MARKET: "sell_market",
  SELL_LIMIT: "sell_limit",
  TRAILING_STOP: "trailing_stop",
  TRAILING_STOP_LIMIT: "trailing_stop_limit",
  TAKE_PROFIT: "take_profit",
  TAKE_PROFIT_LIMIT: "take_profit_limit",
  UNSUPPORTED: "unsupported",
  UNKNOWN: "unknown",
} as const
export type TraderOrderTypeValue = (typeof TraderOrderType)[keyof typeof TraderOrderType]
