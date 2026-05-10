import { describe, it, expect, vi } from "vitest";
import Decimal from "decimal.js";
import type { AbstractExchange } from "@drakkarsoftware/octobot-trading-exchanges";
import { createMarketDataKeywords } from "../src/marketData.js";

// [timestamp, open, high, low, close, volume]
const KLINE = [1234567890, 50000, 55000, 48000, 52000, 100];

const TICKER = {
  last: 52100,
  close: 52000,
  open: 50000,
  high: 55000,
  low: 48000,
  baseVolume: 200,
};

const ORDER_BOOK = {
  bids: [[59900, 0.5], [59800, 1.2]],
  asks: [[60100, 0.3], [60200, 0.8]],
};

function makeExchange(overrides: Partial<Record<string, unknown>> = {}): AbstractExchange {
  return {
    getKlinePrice: vi.fn().mockResolvedValue(KLINE),
    getPriceTicker: vi.fn().mockResolvedValue(TICKER),
    getOrderBook: vi.fn().mockResolvedValue(ORDER_BOOK),
    ...overrides,
  } as unknown as AbstractExchange;
}

describe("createMarketDataKeywords", () => {
  describe("OHLCV keywords", () => {
    it("close returns close price as Decimal", async () => {
      const exchange = makeExchange();
      const kw = createMarketDataKeywords(exchange);
      const v = await kw.close("BTC/USDT", "1h");
      expect(exchange.getKlinePrice).toHaveBeenCalledWith("BTC/USDT", "1h");
      expect(v).toBeInstanceOf(Decimal);
      expect(v.toNumber()).toBe(52000);
    });

    it("open returns open price", async () => {
      const kw = createMarketDataKeywords(makeExchange());
      expect((await kw.open("BTC/USDT", "1h")).toNumber()).toBe(50000);
    });

    it("high returns high price", async () => {
      const kw = createMarketDataKeywords(makeExchange());
      expect((await kw.high("BTC/USDT", "1h")).toNumber()).toBe(55000);
    });

    it("low returns low price", async () => {
      const kw = createMarketDataKeywords(makeExchange());
      expect((await kw.low("BTC/USDT", "1h")).toNumber()).toBe(48000);
    });

    it("volume returns volume", async () => {
      const kw = createMarketDataKeywords(makeExchange());
      expect((await kw.volume("BTC/USDT", "1h")).toNumber()).toBe(100);
    });

    it("time returns timestamp as number", async () => {
      const kw = createMarketDataKeywords(makeExchange());
      expect(await kw.time("BTC/USDT", "1h")).toBe(1234567890);
    });

    it("returns Decimal(0) when kline is null", async () => {
      const kw = createMarketDataKeywords(
        makeExchange({ getKlinePrice: vi.fn().mockResolvedValue(null) }),
      );
      expect((await kw.close("BTC/USDT", "1h")).toNumber()).toBe(0);
    });
  });

  describe("ticker keywords", () => {
    it("ticker_last returns last price", async () => {
      const kw = createMarketDataKeywords(makeExchange());
      expect((await kw.ticker_last("BTC/USDT")).toNumber()).toBe(52100);
    });

    it("ticker_close returns close", async () => {
      const kw = createMarketDataKeywords(makeExchange());
      expect((await kw.ticker_close("BTC/USDT")).toNumber()).toBe(52000);
    });

    it("ticker_open returns open", async () => {
      const kw = createMarketDataKeywords(makeExchange());
      expect((await kw.ticker_open("BTC/USDT")).toNumber()).toBe(50000);
    });

    it("ticker_high returns high", async () => {
      const kw = createMarketDataKeywords(makeExchange());
      expect((await kw.ticker_high("BTC/USDT")).toNumber()).toBe(55000);
    });

    it("ticker_low returns low", async () => {
      const kw = createMarketDataKeywords(makeExchange());
      expect((await kw.ticker_low("BTC/USDT")).toNumber()).toBe(48000);
    });

    it("ticker_volume returns baseVolume", async () => {
      const kw = createMarketDataKeywords(makeExchange());
      expect((await kw.ticker_volume("BTC/USDT")).toNumber()).toBe(200);
    });

    it("returns Decimal(0) when ticker is null", async () => {
      const kw = createMarketDataKeywords(
        makeExchange({ getPriceTicker: vi.fn().mockResolvedValue(null) }),
      );
      expect((await kw.ticker_last("BTC/USDT")).toNumber()).toBe(0);
    });
  });

  describe("order book keywords", () => {
    it("bid returns best bid price", async () => {
      const exchange = makeExchange();
      const kw = createMarketDataKeywords(exchange);
      const v = await kw.bid("BTC/USDT");
      expect(exchange.getOrderBook).toHaveBeenCalledWith("BTC/USDT", 1);
      expect(v).toBeInstanceOf(Decimal);
      expect(v.toNumber()).toBe(59900);
    });

    it("ask returns best ask price", async () => {
      const kw = createMarketDataKeywords(makeExchange());
      expect((await kw.ask("BTC/USDT")).toNumber()).toBe(60100);
    });

    it("bid_volume returns best bid amount", async () => {
      const kw = createMarketDataKeywords(makeExchange());
      expect((await kw.bid_volume("BTC/USDT")).toNumber()).toBe(0.5);
    });

    it("ask_volume returns best ask amount", async () => {
      const kw = createMarketDataKeywords(makeExchange());
      expect((await kw.ask_volume("BTC/USDT")).toNumber()).toBe(0.3);
    });

    it("returns Decimal(0) when order book is null", async () => {
      const kw = createMarketDataKeywords(
        makeExchange({ getOrderBook: vi.fn().mockResolvedValue(null) }),
      );
      expect((await kw.bid("BTC/USDT")).toNumber()).toBe(0);
      expect((await kw.ask("BTC/USDT")).toNumber()).toBe(0);
    });
  });
});
