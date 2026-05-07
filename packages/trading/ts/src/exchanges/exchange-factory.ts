// Mirrors octobot_trading/exchanges/exchange_factory.py
import type { ExchangeConfig } from "../types/index.js"
import { BinanceExchange } from "./implementations/binance/binance-exchange.js"
import { BybitExchange } from "./implementations/bybit/bybit-exchange.js"
import { DefaultRestExchange } from "./implementations/default-rest-exchange.js"
import type { RestExchange } from "./types/rest-exchange.js"

export const EXCHANGE_REGISTRY: Record<string, new (config: ExchangeConfig) => RestExchange> = {
  binance: BinanceExchange,
  bybit: BybitExchange,
}

export function createExchange(config: ExchangeConfig): RestExchange {
  const ExchangeClass = EXCHANGE_REGISTRY[config.exchangeName] ?? DefaultRestExchange
  return new ExchangeClass(config)
}
