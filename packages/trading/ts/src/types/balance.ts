export interface PortfolioCurrency {
  free: number
  used: number
  total: number
}

export type OctoBotBalance = Record<string, PortfolioCurrency>
