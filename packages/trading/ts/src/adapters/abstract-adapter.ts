// Mirrors octobot_trading/exchanges/adapters/abstract_adapter.py
import type * as ccxt from "ccxt"

import { UnexpectedAdapterError } from "../errors/base.js"
import type {
  OctoBotBalance,
  OctoBotDepositAddress,
  OctoBotFundingRate,
  OctoBotLeverageTier,
  OctoBotMarketStatus,
  OctoBotOHLCV,
  OctoBotOrder,
  OctoBotOrderBook,
  OctoBotPosition,
  OctoBotTicker,
  OctoBotTrade,
  OctoBotTransaction,
} from "../types/index.js"

// Timestamp threshold: > this value means milliseconds (year 2500 = 16728292300 seconds)
const MS_TIMESTAMP_THRESHOLD = 16728292300

// Mirrors Python's @_adapter decorator — wraps null-check and error conversion
function makeAdapter<TRaw, TResult>(
  fn: (self: AbstractAdapter, raw: TRaw, opts?: Record<string, unknown>) => TResult,
): (
  self: AbstractAdapter,
  raw: TRaw | null | undefined,
  opts?: Record<string, unknown>,
) => TResult | null {
  return (self, raw, opts) => {
    if (raw === null || raw === undefined) return null
    try {
      return fn(self, raw, opts)
    } catch (err) {
      throw new UnexpectedAdapterError(
        `Unexpected error when adapting exchange data: ${err} (data: ${JSON.stringify(raw)})`,
      )
    }
  }
}

export abstract class AbstractAdapter {
  constructor(protected readonly connector: unknown) {}

  // Timestamp uniformization: ms → seconds
  // mirrors AbstractAdapter.get_uniformized_timestamp
  getUniformizedTimestamp(ts: number | null | undefined): number | null {
    if (ts === null || ts === undefined) return null
    return ts > MS_TIMESTAMP_THRESHOLD ? ts / 1000 : ts
  }

  // ── adapt_* wrappers (null-safe + error-wrapped) ─────────────────────────

  adaptOrder(raw: ccxt.Order | null | undefined, opts?: Record<string, unknown>): OctoBotOrder | null {
    return makeAdapter<ccxt.Order, OctoBotOrder>((self, r, o) => {
      const fixed = self.fixOrder(r as unknown as Record<string, unknown>, o)
      return self.parseOrder(fixed, o)
    })(this, raw, opts)
  }

  adaptOrders(
    raw: ccxt.Order[] | null | undefined,
    opts?: Record<string, unknown> & { cancelledOnly?: boolean },
  ): OctoBotOrder[] | null {
    return makeAdapter<ccxt.Order[], OctoBotOrder[]>((self, r, o) => {
      const cancelledOnly = (o as { cancelledOnly?: boolean } | undefined)?.cancelledOnly ?? false
      return r
        .map((item) => self.adaptOrder(item, o))
        .filter((order): order is OctoBotOrder => {
          if (!order) return false
          if (!cancelledOnly) return true
          return order.status === "canceled"
        })
    })(this, raw, opts)
  }

  adaptOhlcv(
    raw: ccxt.OHLCV[] | null | undefined,
    opts?: Record<string, unknown>,
  ): OctoBotOHLCV[] | null {
    return makeAdapter<ccxt.OHLCV[], OctoBotOHLCV[]>((self, r, o) => {
      const fixed = self.fixOhlcv(r, o)
      return self.parseOhlcv(fixed, o)
    })(this, raw, opts)
  }

  adaptKline(
    raw: ccxt.OHLCV[] | null | undefined,
    opts?: Record<string, unknown>,
  ): OctoBotOHLCV[] | null {
    return makeAdapter<ccxt.OHLCV[], OctoBotOHLCV[]>((self, r, o) => {
      const fixed = self.fixKline(r, o)
      return self.parseKline(fixed, o)
    })(this, raw, opts)
  }

  adaptTicker(
    raw: ccxt.Ticker | null | undefined,
    opts?: Record<string, unknown>,
  ): OctoBotTicker | null {
    return makeAdapter<ccxt.Ticker, OctoBotTicker>((self, r, o) => {
      const fixed = self.fixTicker(r, o)
      return self.parseTicker(fixed, o)
    })(this, raw, opts)
  }

  adaptBalance(
    raw: ccxt.Balances | null | undefined,
    opts?: Record<string, unknown>,
  ): OctoBotBalance | null {
    return makeAdapter<ccxt.Balances, OctoBotBalance>((self, r, o) => {
      const fixed = self.fixBalance(r, o)
      return self.parseBalance(fixed, o)
    })(this, raw, opts)
  }

  adaptOrderBook(
    raw: ccxt.OrderBook | null | undefined,
    opts?: Record<string, unknown>,
  ): OctoBotOrderBook | null {
    return makeAdapter<ccxt.OrderBook, OctoBotOrderBook>((self, r, o) => {
      const fixed = self.fixOrderBook(r, o)
      return self.parseOrderBook(fixed, o)
    })(this, raw, opts)
  }

  adaptPublicRecentTrades(
    raw: ccxt.Trade[] | null | undefined,
    opts?: Record<string, unknown>,
  ): OctoBotTrade[] | null {
    return makeAdapter<ccxt.Trade[], OctoBotTrade[]>((self, r, o) => {
      const fixed = self.fixPublicRecentTrades(r, o)
      return self.parsePublicRecentTrades(fixed, o)
    })(this, raw, opts)
  }

  adaptTrades(
    raw: ccxt.Trade[] | null | undefined,
    opts?: Record<string, unknown>,
  ): OctoBotTrade[] | null {
    return makeAdapter<ccxt.Trade[], OctoBotTrade[]>((self, r, o) => {
      const fixed = self.fixTrades(r, o)
      return self.parseTrades(fixed, o)
    })(this, raw, opts)
  }

  adaptPosition(
    raw: ccxt.Position | null | undefined,
    opts?: Record<string, unknown>,
  ): OctoBotPosition | null {
    return makeAdapter<ccxt.Position, OctoBotPosition>((self, r, o) => {
      const fixed = self.fixPosition(r, o)
      return self.parsePosition(fixed, o)
    })(this, raw, opts)
  }

  adaptFundingRate(
    raw: ccxt.FundingRate | null | undefined,
    opts?: Record<string, unknown>,
  ): OctoBotFundingRate | null {
    return makeAdapter<ccxt.FundingRate, OctoBotFundingRate>((self, r, o) => {
      const fixed = self.fixFundingRate(r, o)
      return self.parseFundingRate(fixed, o)
    })(this, raw, opts)
  }

  adaptLeverageTiers(
    raw: ccxt.LeverageTiers | null | undefined,
    opts?: Record<string, unknown>,
  ): Record<string, OctoBotLeverageTier[]> | null {
    return makeAdapter<ccxt.LeverageTiers, Record<string, OctoBotLeverageTier[]>>((self, r, o) => {
      const fixed = self.fixLeverageTiers(r, o)
      return self.parseLeverageTiers(fixed, o)
    })(this, raw, opts)
  }

  adaptMarketStatus(
    raw: ccxt.Market | null | undefined,
    opts?: Record<string, unknown>,
  ): OctoBotMarketStatus | null {
    return makeAdapter<ccxt.Market, OctoBotMarketStatus>((self, r, o) => {
      const fixed = self.fixMarketStatus(r, o)
      return self.parseMarketStatus(fixed, o)
    })(this, raw, opts)
  }

  adaptTransaction(
    raw: ccxt.Transaction | null | undefined,
    opts?: Record<string, unknown>,
  ): OctoBotTransaction | null {
    return makeAdapter<ccxt.Transaction, OctoBotTransaction>((self, r, o) => {
      const fixed = self.fixTransaction(r, o)
      return self.parseTransaction(fixed, o)
    })(this, raw, opts)
  }

  adaptDepositAddress(
    raw: ccxt.DepositAddress | null | undefined,
    opts?: Record<string, unknown>,
  ): OctoBotDepositAddress | null {
    return makeAdapter<ccxt.DepositAddress, OctoBotDepositAddress>((self, r, o) => {
      const fixed = self.fixDepositAddress(r, o)
      return self.parseDepositAddress(fixed, o)
    })(this, raw, opts)
  }

  // ── fix_* methods (default identity, override in subclass) ───────────────

  fixOrder(raw: Record<string, unknown>, _opts?: Record<string, unknown>): Record<string, unknown> {
    const fixed = { ...raw }
    // mirrors AbstractAdapter.fix_order: id → exchange_id
    if ("id" in fixed) {
      fixed["exchange_id"] = fixed["id"]
      delete fixed["id"]
    }
    return fixed
  }

  fixOhlcv(raw: ccxt.OHLCV[], _opts?: Record<string, unknown>): ccxt.OHLCV[] {
    return raw
  }

  fixKline(raw: ccxt.OHLCV[], _opts?: Record<string, unknown>): ccxt.OHLCV[] {
    return raw
  }

  fixTicker(raw: ccxt.Ticker, _opts?: Record<string, unknown>): ccxt.Ticker {
    return raw
  }

  fixBalance(raw: ccxt.Balances, _opts?: Record<string, unknown>): ccxt.Balances {
    return raw
  }

  fixOrderBook(raw: ccxt.OrderBook, _opts?: Record<string, unknown>): ccxt.OrderBook {
    return raw
  }

  fixPublicRecentTrades(raw: ccxt.Trade[], _opts?: Record<string, unknown>): ccxt.Trade[] {
    return raw
  }

  fixTrades(raw: ccxt.Trade[], _opts?: Record<string, unknown>): ccxt.Trade[] {
    // mirrors AbstractAdapter.fix_trades: id → exchange_trade_id
    for (const trade of raw) {
      const t = trade as unknown as Record<string, unknown>
      if ("id" in t) {
        t["exchange_trade_id"] = t["id"]
        delete t["id"]
      }
    }
    return raw
  }

  fixPosition(raw: ccxt.Position, _opts?: Record<string, unknown>): ccxt.Position {
    return raw
  }

  fixFundingRate(raw: ccxt.FundingRate, _opts?: Record<string, unknown>): ccxt.FundingRate {
    return raw
  }

  fixLeverageTiers(
    raw: ccxt.LeverageTiers,
    _opts?: Record<string, unknown>,
  ): ccxt.LeverageTiers {
    return raw
  }

  fixMarketStatus(raw: ccxt.Market, _opts?: Record<string, unknown>): ccxt.Market {
    return raw
  }

  fixTransaction(raw: ccxt.Transaction, _opts?: Record<string, unknown>): ccxt.Transaction {
    return raw
  }

  fixDepositAddress(
    raw: ccxt.DepositAddress,
    _opts?: Record<string, unknown>,
  ): ccxt.DepositAddress {
    return raw
  }

  // ── parse_* methods (abstract — must be implemented in subclass) ─────────

  abstract parseOrder(
    fixed: Record<string, unknown>,
    opts?: Record<string, unknown>,
  ): OctoBotOrder

  abstract parseOhlcv(fixed: ccxt.OHLCV[], opts?: Record<string, unknown>): OctoBotOHLCV[]

  abstract parseKline(fixed: ccxt.OHLCV[], opts?: Record<string, unknown>): OctoBotOHLCV[]

  abstract parseTicker(fixed: ccxt.Ticker, opts?: Record<string, unknown>): OctoBotTicker

  abstract parseBalance(fixed: ccxt.Balances, opts?: Record<string, unknown>): OctoBotBalance

  abstract parseOrderBook(
    fixed: ccxt.OrderBook,
    opts?: Record<string, unknown>,
  ): OctoBotOrderBook

  abstract parsePublicRecentTrades(
    fixed: ccxt.Trade[],
    opts?: Record<string, unknown>,
  ): OctoBotTrade[]

  abstract parseTrades(fixed: ccxt.Trade[], opts?: Record<string, unknown>): OctoBotTrade[]

  abstract parsePosition(fixed: ccxt.Position, opts?: Record<string, unknown>): OctoBotPosition

  abstract parseFundingRate(
    fixed: ccxt.FundingRate,
    opts?: Record<string, unknown>,
  ): OctoBotFundingRate

  abstract parseLeverageTiers(
    fixed: ccxt.LeverageTiers,
    opts?: Record<string, unknown>,
  ): Record<string, OctoBotLeverageTier[]>

  abstract parseMarketStatus(
    fixed: ccxt.Market,
    opts?: Record<string, unknown>,
  ): OctoBotMarketStatus

  abstract parseTransaction(
    fixed: ccxt.Transaction,
    opts?: Record<string, unknown>,
  ): OctoBotTransaction

  abstract parseDepositAddress(
    fixed: ccxt.DepositAddress,
    opts?: Record<string, unknown>,
  ): OctoBotDepositAddress
}
