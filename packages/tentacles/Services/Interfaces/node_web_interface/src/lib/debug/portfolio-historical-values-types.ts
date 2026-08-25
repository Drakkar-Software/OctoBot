export type HistoricalAssetValue = {
  symbol: string
  holdings: number
  value: number
}

export type HistoricalAssetsForTradingType = {
  trading_type: string
  assets: HistoricalAssetValue[]
}

export type PortfolioHistoricalValue = {
  timestamp: string
  total: number
  assets?: HistoricalAssetsForTradingType[] | null
}

export type PortfolioHistoricalValues = {
  unit: string
  values: PortfolioHistoricalValue[]
}

export type PortfolioHistoricalValuesState = {
  version: string
  history?: PortfolioHistoricalValues | null
}
