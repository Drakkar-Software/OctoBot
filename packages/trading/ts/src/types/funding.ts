export interface OctoBotFundingRate {
  symbol: string
  funding_rate: number
  last_funding_time: number
  next_funding_time: number
  predicted_funding_rate: number
}

export interface OctoBotLeverageTier {
  tier: number
  currency: string
  min_notional: number
  max_notional: number
  maintenance_margin_rate: number
  max_leverage: number
  info?: Record<string, unknown>
}
