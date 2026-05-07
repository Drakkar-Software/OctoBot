// Mirrors Python's Bybit tentacle exchange overrides
import type { ExchangeConfig } from "../../../types/index.js"
import { RestExchange } from "../../types/rest-exchange.js"

export class BybitExchange extends RestExchange {
  static override FIX_MARKET_STATUS = true
  static override REMOVE_MARKET_STATUS_PRICE_LIMITS = false
  static override SUPPORTS_FETCHING_CANCELLED_ORDERS = false

  static override EXCHANGE_ORDER_NOT_FOUND_ERRORS: string[][] = [
    ["Order does not exist"],
    ["order not found"],
  ]

  static override getName(): string {
    return "bybit"
  }

  constructor(config: ExchangeConfig) {
    super({ ...config, exchangeName: "bybit" })
  }
}
