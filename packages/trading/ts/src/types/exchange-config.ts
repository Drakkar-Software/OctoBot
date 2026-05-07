export interface CredentialsData {
  apiKey?: string
  secret?: string
  password?: string
  uid?: string
}

export interface ExchangeConfig {
  exchangeName: string
  credentials?: CredentialsData
  sandbox?: boolean
  options?: Record<string, unknown>
  isFuture?: boolean
}
