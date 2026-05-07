// Mirrors Python's Binance tentacle exchange overrides
import type { ExchangeConfig } from "../../../types/index.js"
import { RestExchange } from "../../types/rest-exchange.js"
import type { CCXTAdapter } from "../../../adapters/ccxt-adapter.js"

export class BinanceExchange extends RestExchange {
  // Binance-specific flags (mirrors Python Binance tentacle)
  static override FIX_MARKET_STATUS = true
  static override REMOVE_MARKET_STATUS_PRICE_LIMITS = false
  static override CONVERT_ORDER_SIZE_BEFORE_PUSHING_TO_EXCHANGES = true
  static override SUPPORTS_FETCHING_CANCELLED_ORDERS = false
  static override CAN_MISS_TICKERS_IN_ALL_TICKERS = true

  static override EXCHANGE_ORDER_NOT_FOUND_ERRORS: string[][] = [
    ["Order does not exist"],
    ["order id does not exist"],
  ]

  static override getName(): string {
    return "binance"
  }

  constructor(config: ExchangeConfig) {
    super({ ...config, exchangeName: "binance" })
  }
}
