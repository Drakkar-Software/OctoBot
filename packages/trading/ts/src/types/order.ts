import type { OrderStatusValue, TradeOrderSideValue, TradeOrderTypeValue } from "../enums/index.js"

export interface FeeData {
  type: string | null
  currency: string | null
  rate: number | null
  cost: number
  is_from_exchange: boolean
  exchange_original_cost: number | null
}

export interface OctoBotOrder {
  exchange_id: string
  timestamp: number
  symbol: string
  type: TradeOrderTypeValue | string
  side: TradeOrderSideValue
  price: number | null
  amount: number
  filled: number
  remaining: number
  cost: number | null
  average: number | null
  status: OrderStatusValue | string
  fee: FeeData | null
  reduceOnly: boolean
  stopPrice: number | null
  stopLossPrice: number | null
  takeProfitPrice: number | null
  triggerAbove: boolean | null
  info?: Record<string, unknown>
}

export interface OctoBotTrade extends OctoBotOrder {
  exchange_trade_id: string | null
  order_id: string | null
  takerOrMaker: "taker" | "maker" | null
}
