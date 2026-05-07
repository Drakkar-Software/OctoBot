export interface OctoBotTransaction {
  id: string
  txid?: string | null
  timestamp: number | null
  address_from?: string | null
  address_to?: string | null
  tag?: string | null
  type: string
  amount: number
  currency: string
  status: string
  fee?: number | null
  network?: string | null
  comment?: string | null
  internal?: boolean
  info?: Record<string, unknown>
}

export interface OctoBotDepositAddress {
  currency: string
  network?: string | null
  address: string
  tag?: string | null
  info?: Record<string, unknown>
}
