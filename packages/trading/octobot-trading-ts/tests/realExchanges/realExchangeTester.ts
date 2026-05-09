// Declarative real-exchange test base. Mirrors the inheritance-based design of
// tests_additional/real_exchanges/real_exchange_tester.py — but instead of
// per-exchange subclasses, callers register a config object and a Vitest suite
// is generated automatically. Gated behind VITEST_REAL_EXCHANGES=1 so live API
// calls aren't made by accident in CI.

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { ExchangeBuilder } from "../../src/exchangeBuilder.js";
import type { ExchangeManager } from "../../src/exchangeManager.js";
import { ExchangeConstantsMarketStatusColumns as EMSC } from "../../src/enums.js";

export interface RealExchangeSpec {
  exchangeName: string;
  symbol: string;
  symbol2?: string;
  symbol3?: string;
  timeFrame?: string;
  marketStatusType?: string;
  requiresAuth?: boolean;
  apiKey?: string;
  apiSecret?: string;
  apiPassword?: string;
  isFuture?: boolean;
  isMargin?: boolean;
  isOption?: boolean;
  candleSinceMs?: number;
  defaultBookLimit?: number;
  orderBookDesyncAllowanceSeconds?: number;
}

const SHOULD_RUN = process.env.VITEST_REAL_EXCHANGES === "1";

export function defineRealExchangeSuite(spec: RealExchangeSpec): void {
  const skipReason = !SHOULD_RUN
    ? "Skipped — set VITEST_REAL_EXCHANGES=1 to enable live exchange tests"
    : null;

  const guarded = (name: string, fn: () => Promise<void> | void) => {
    if (skipReason) it.skip(`${name} (${skipReason})`, () => undefined);
    else it(name, fn, 30_000);
  };

  describe(`real exchange: ${spec.exchangeName}`, () => {
    let manager: ExchangeManager;

    beforeAll(async () => {
      if (skipReason) return;
      const builder = new ExchangeBuilder(spec.exchangeName);
      if (spec.isFuture) builder.asFuture();
      else if (spec.isMargin) builder.asMargin();
      else if (spec.isOption) builder.asOption();
      else builder.asSpot();
      if (spec.apiKey || spec.apiSecret || spec.apiPassword) {
        builder.setCredentials({
          apiKey: spec.apiKey,
          secret: spec.apiSecret,
          password: spec.apiPassword,
        });
      }
      manager = builder.build();
      await manager.initialize();
    }, 60_000);

    afterAll(async () => {
      if (manager) await manager.stop();
    });

    guarded("market status is well-formed for the primary symbol", async () => {
      const ms = manager.exchange!.getMarketStatus(spec.symbol);
      expect(ms).toBeTruthy();
      expect(ms[EMSC.SYMBOL]).toBe(spec.symbol);
    });

    guarded("fetches OHLCV for the configured timeframe", async () => {
      const tf = spec.timeFrame ?? "1h";
      const candles = await manager.exchange!.getSymbolPrices(spec.symbol, tf, 5);
      expect(Array.isArray(candles)).toBe(true);
      expect((candles as unknown[][]).length).toBeGreaterThan(0);
    });

    guarded("fetches a ticker", async () => {
      const ticker = await manager.exchange!.getPriceTicker(spec.symbol);
      expect(ticker).toBeTruthy();
    });

    guarded("fetches an order book", async () => {
      const ob = await manager.exchange!.getOrderBook(spec.symbol, spec.defaultBookLimit ?? 5);
      expect(ob).toBeTruthy();
      const obj = ob as Record<string, unknown>;
      expect(Array.isArray(obj["bids"])).toBe(true);
      expect(Array.isArray(obj["asks"])).toBe(true);
    });

    guarded("fetches recent trades", async () => {
      const trades = await manager.exchange!.getRecentTrades(spec.symbol, 10);
      expect(Array.isArray(trades)).toBe(true);
    });

    guarded("ts: ticker timestamp is recent (within order-book desync allowance)", async () => {
      const ticker = await manager.exchange!.getPriceTicker(spec.symbol);
      const ts = (ticker as Record<string, unknown>)["timestamp"] as number | undefined;
      if (ts !== undefined && ts !== null) {
        const allowance = spec.orderBookDesyncAllowanceSeconds ?? 60;
        const nowSeconds = Date.now() / 1000;
        const tickerSeconds = ts < 1e12 ? ts : ts / 1000;
        expect(Math.abs(nowSeconds - tickerSeconds)).toBeLessThan(allowance + 60);
      }
    });
  });
}
