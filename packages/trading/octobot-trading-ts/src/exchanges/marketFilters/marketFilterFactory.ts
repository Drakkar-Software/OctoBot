import {
  ExchangeConstantsMarketStatusColumns as Ecmsc,
  ExchangeTypes,
} from "../enums.js";
import type { ExchangeData } from "../util/exchangeData.js";

const USD_LIKE_COINS: ReadonlySet<string> = new Set([
  "USD",
  "USDT",
  "USDC",
  "BUSD",
  "DAI",
  "TUSD",
  "USDP",
  "USDD",
  "FDUSD",
]);

export interface CreateMarketFilterOptions {
  exchangeData?: ExchangeData | null;
  toKeepQuote?: string | null;
  toKeepSymbols?: Iterable<string>;
  toKeepQuotes?: Iterable<string>;
  forceUsdLikeMarkets?: boolean;
}

/**
 * Mirror of market_filters/market_filter_factory.py — returns a predicate
 * that decides whether a CCXT market should be retained for a strategy.
 */
export function createMarketFilter(opts: CreateMarketFilterOptions): (market: Record<string, unknown>) => boolean {
  const relevantSymbolsToKeep = new Set<string>(opts.toKeepSymbols ?? []);
  if (opts.exchangeData) {
    for (const m of opts.exchangeData.markets) relevantSymbolsToKeep.add(m.symbol);
    for (const o of opts.exchangeData.ordersDetails.openOrders) {
      const s = o["symbol"];
      if (typeof s === "string") relevantSymbolsToKeep.add(s);
    }
    for (const p of opts.exchangeData.positions) {
      const s = p.position["symbol"];
      if (typeof s === "string") relevantSymbolsToKeep.add(s);
    }
  }
  const mergedToKeepQuotes = new Set<string>(opts.toKeepQuotes ?? []);
  if (opts.toKeepQuote) mergedToKeepQuotes.add(opts.toKeepQuote);
  const forceUsdLike = opts.forceUsdLikeMarkets ?? true;

  return (market: Record<string, unknown>): boolean => {
    const symbol = market[Ecmsc.SYMBOL] as string | undefined;
    if (symbol && relevantSymbolsToKeep.has(symbol)) return true;
    const base = market[Ecmsc.CURRENCY] as string | undefined;
    const quote = market[Ecmsc.MARKET] as string | undefined;
    const type = market[Ecmsc.TYPE] as string | undefined;
    return (
      ((quote && mergedToKeepQuotes.has(quote)) ||
        (base && mergedToKeepQuotes.has(base)) ||
        (forceUsdLike && base !== undefined && USD_LIKE_COINS.has(base))) &&
      type === ExchangeTypes.SPOT
    );
  };
}
