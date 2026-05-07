export interface OctoBotTicker {
  symbol: string
  timestamp: number | null
  datetime?: string | null
  high: number | null
  low: number | null
  bid: number | null
  bidVolume: number | null
  ask: number | null
  askVolume: number | null
  vwap: number | null
  open: number | null
  close: number | null
  last: number | null
  previousClose: number | null
  change: number | null
  percentage: number | null
  average: number | null
  baseVolume: number | null
  quoteVolume: number | null
  info?: Record<string, unknown>
}
