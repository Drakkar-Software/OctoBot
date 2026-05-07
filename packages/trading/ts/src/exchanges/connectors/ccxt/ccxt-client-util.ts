// Mirrors octobot_trading/exchanges/connectors/ccxt/ccxt_client_util.py
import * as ccxt from "ccxt"
import type { ExchangeConfig } from "../../../types/index.js"

export function createCcxtClient(config: ExchangeConfig): ccxt.Exchange {
  const exchangeId = config.exchangeName
  // ccxt exports all exchange classes as named properties
  const ExchangeClass = (ccxt as unknown as Record<string, new (opts: object) => ccxt.Exchange>)[
    exchangeId
  ]
  if (!ExchangeClass) {
    throw new Error(`Exchange "${exchangeId}" not found in ccxt. Available: ${Object.keys(ccxt.exchanges).join(", ")}`)
  }
  const opts: Record<string, unknown> = {
    enableRateLimit: true,
  }
  if (config.credentials?.apiKey) opts["apiKey"] = config.credentials.apiKey
  if (config.credentials?.secret) opts["secret"] = config.credentials.secret
  if (config.credentials?.password) opts["password"] = config.credentials.password
  if (config.credentials?.uid) opts["uid"] = config.credentials.uid
  if (config.sandbox) {
    opts["sandbox"] = true
  }
  if (config.options) {
    opts["options"] = config.options
  }
  return new ExchangeClass(opts)
}

export function mapOrderTypeToCcxt(
  orderType: string,
  side?: string,
): { ccxtType: string; ccxtSide: string } {
  // mirrors how Python maps TraderOrderType → CCXT type + side
  const sideMap: Record<string, string> = {
    buy_market: "buy",
    buy_limit: "buy",
    sell_market: "sell",
    sell_limit: "sell",
    stop_loss: side ?? "sell",
    stop_limit: side ?? "sell",
    take_profit: side ?? "buy",
    take_profit_limit: side ?? "buy",
    trailing_stop: side ?? "sell",
    trailing_stop_limit: side ?? "sell",
  }
  const typeMap: Record<string, string> = {
    buy_market: "market",
    buy_limit: "limit",
    sell_market: "market",
    sell_limit: "limit",
    stop_loss: "stop_loss",
    stop_limit: "stop_limit",
    take_profit: "take_profit",
    take_profit_limit: "take_profit_limit",
    trailing_stop: "trailing_stop",
    trailing_stop_limit: "trailing_stop_limit",
  }
  return {
    ccxtType: typeMap[orderType] ?? orderType,
    ccxtSide: sideMap[orderType] ?? (side ?? "buy"),
  }
}

export function getContractSize(client: ccxt.Exchange, symbol: string): number {
  try {
    const market = client.market(symbol)
    return Number((market as unknown as Record<string, unknown>)["contractSize"] ?? 1) || 1
  } catch {
    return 1
  }
}
