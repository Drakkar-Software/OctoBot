export interface MarketLimitRange {
  min: number | null
  max: number | null
}

export interface MarketLimits {
  amount: MarketLimitRange
  price: MarketLimitRange
  cost: MarketLimitRange
}

export interface MarketPrecision {
  price: number | null
  amount: number | null
  cost?: number | null
}

export interface OctoBotMarketStatus {
  symbol: string
  id?: string
  base: string
  quote: string
  active: boolean
  precision: MarketPrecision
  limits: MarketLimits
  type: string
  expiry?: string | null
  taker?: number | null
  maker?: number | null
  info?: Record<string, unknown>
}
