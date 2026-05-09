// Slimmed port of util/exchange_util.py (~647 LOC). Most of the original is
// tentacle-loading and registry plumbing tied to octobot_tentacles_manager.
// We keep the helpers that stay useful in a browser context.

import {
  ExchangeConstantsOrderColumns as EOC,
  TradeOrderSide,
  ExchangeTypes,
} from "../enums.js";
import {
  AuthenticationError,
  FailedRequest,
  NetworkError,
  NotSupported,
  RateLimitExceeded,
  OctoBotExchangeError,
  OctoBotTradingError,
} from "../errors.js";
import type { Logger } from "@drakkarsoftware/octobot-commons";
import { Exchanges } from "../exchanges.js";

/**
 * Mirror of util/exchange_util.exchange_error_translator. Maps a thrown error
 * (CCXT or generic) to the closest typed OctoBot trading error.
 */
export function exchangeErrorTranslator(err: unknown, defaultMessage = "Exchange error"): OctoBotTradingError {
  if (err instanceof OctoBotTradingError) return err;
  const e = err as Error;
  const msg = e?.message || defaultMessage;
  const name = e?.constructor?.name ?? "";
  if (name.includes("Auth")) return new AuthenticationError(msg);
  if (name.includes("RateLimit")) return new RateLimitExceeded(msg);
  if (name.includes("NotSupported")) return new NotSupported(msg);
  if (name.includes("Network") || name.includes("Timeout")) return new NetworkError(msg);
  return new FailedRequest(msg);
}

/** Returns the side derived from a parsed order dict. */
export function getOrderSide(rawOrder: Record<string, unknown>): TradeOrderSide | null {
  const side = rawOrder[EOC.SIDE] as string | undefined;
  if (side === TradeOrderSide.BUY) return TradeOrderSide.BUY;
  if (side === TradeOrderSide.SELL) return TradeOrderSide.SELL;
  return null;
}

export function isMissingTradingFees(order: Record<string, unknown>): boolean {
  const fee = order[EOC.FEE];
  if (!fee || typeof fee !== "object") return true;
  const f = fee as Record<string, unknown>;
  return f["cost"] === null || f["cost"] === undefined;
}

export function applyTradesFees(_orders: Record<string, unknown>[], _trades: Record<string, unknown>[]): void {
  // Server-side computation lives in personal_data.fees_util in Python; the
  // browser wrapper exposes the function as a no-op so callers can swap a
  // custom implementation. This keeps the public re-export shape the same.
}

export function logTimeSyncError(logger: Logger, exchangeName: string, err: unknown): void {
  logger.warning(`[${exchangeName}] time-sync error: ${(err as Error).message}`);
}

export function getEnabledExchanges(): string[] {
  return Exchanges.getExchangesNames();
}

export function isAuthRequiredExchanges(_exchangeName: string): boolean {
  // CEXes generally require auth for trading; this hook is overridable.
  return true;
}

export function isErrorOnThisType(err: unknown, type: typeof OctoBotExchangeError | typeof OctoBotTradingError): boolean {
  return err instanceof type;
}

/** Mirror of util/exchange_util.get_default_exchange_type. */
export function getDefaultExchangeType(): ExchangeTypes {
  return ExchangeTypes.SPOT;
}

export function getSupportedExchangeTypes(): ExchangeTypes[] {
  return [ExchangeTypes.SPOT, ExchangeTypes.FUTURE, ExchangeTypes.MARGIN];
}

export function getCommonTradedQuote(symbols: string[]): string | null {
  const counts = new Map<string, number>();
  for (const s of symbols) {
    const [, quote] = s.split("/");
    if (!quote) continue;
    counts.set(quote, (counts.get(quote) ?? 0) + 1);
  }
  let bestQuote: string | null = null;
  let bestCount = 0;
  for (const [q, c] of counts) {
    if (c > bestCount) {
      bestQuote = q;
      bestCount = c;
    }
  }
  return bestQuote;
}

export function getAssociatedSymbol(symbols: string[], asset: string, quote: string): string | null {
  const wanted = `${asset}/${quote}`;
  return symbols.find((s) => s === wanted) ?? null;
}

export function supportsWebsocket(exchangeName: string): boolean {
  // Forward-declared registry hook. Subclasses can swap this with a fixed list.
  // Default: assume CCXT exchanges that have `has.ws` will support it; we
  // err on the side of "true" so callers can probe and stop on NotSupported.
  void exchangeName;
  return true;
}

export function forceDisableWebSocket(): boolean {
  return false;
}

export function checkWebSocketConfig(_exchangeName: string): boolean {
  return true;
}

export function isProxyConfigCompatibleWithWebSocketConnector(_proxy: unknown): boolean {
  return true;
}
