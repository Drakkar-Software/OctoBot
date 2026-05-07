// Mirrors octobot_trading/exchanges/connectors/ccxt/ccxt_client_util.py:converted_ccxt_common_errors
import * as ccxt from "ccxt"

import {
  AuthenticationError,
  ExchangeCompliancyError,
  ExchangeInternalSyncError,
  FailedRequest,
  MarketClosedError,
  MissingFunds,
  NetworkError,
  NotSupported,
  RateLimitExceeded,
  UnSupportedSymbolError,
} from "./base.js"

export async function withCcxtErrorConversion<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn()
  } catch (err) {
    if (err instanceof ccxt.RateLimitExceeded) throw new RateLimitExceeded(String(err))
    if (err instanceof ccxt.DDoSProtection) throw new RateLimitExceeded(String(err))
    if (err instanceof ccxt.AuthenticationError) throw new AuthenticationError(String(err))
    if (err instanceof ccxt.PermissionDenied) throw new AuthenticationError(String(err))
    if (err instanceof ccxt.InsufficientFunds) throw new MissingFunds(String(err))
    if (err instanceof ccxt.InvalidOrder) throw new FailedRequest(String(err))
    if (err instanceof ccxt.BadSymbol) throw new UnSupportedSymbolError(String(err))
    if (err instanceof ccxt.NotSupported) throw new NotSupported(String(err))
    if (err instanceof ccxt.MarketClosed) throw new MarketClosedError(String(err))
    if (err instanceof ccxt.NetworkError) throw new NetworkError(String(err))
    if (err instanceof ccxt.OnMaintenance) throw new ExchangeInternalSyncError(String(err))
    if (err instanceof ccxt.AccountSuspended) throw new ExchangeCompliancyError(String(err))
    if (err instanceof ccxt.BaseError) throw new FailedRequest(String(err))
    throw err
  }
}

export function isOrderNotFoundError(err: unknown, patterns: string[][]): boolean {
  if (!(err instanceof Error)) return false
  const msg = err.message.toLowerCase()
  return patterns.some((group) => group.every((p) => msg.includes(p.toLowerCase())))
}
