import type { MarginTypeValue, PositionModeValue, PositionSideValue } from "../enums/index.js"

export interface OctoBotPosition {
  symbol: string
  timestamp: number
  side: PositionSideValue
  margin_type: MarginTypeValue | null
  size: number
  notional: number
  collateral: number
  initial_margin: number
  unrealised_pnl: number
  realised_pnl: number
  liquidation_price: number
  mark_price: number
  entry_price: number
  leverage: number
  position_mode: PositionModeValue
  contract_type?: string
  contract_size?: number
  auto_deposit_margin: boolean
}
