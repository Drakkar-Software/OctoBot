// Each entry is [price, amount]
export type OrderBookEntry = [number, number]

export interface OctoBotOrderBook {
  bids: OrderBookEntry[]
  asks: OrderBookEntry[]
  timestamp: number | null
  datetime?: string | null
  nonce?: number | null
}
