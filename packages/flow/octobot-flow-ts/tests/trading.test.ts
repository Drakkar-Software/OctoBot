import { describe, it, expect, vi } from "vitest";
import Decimal from "decimal.js";
import type { AbstractExchange } from "@drakkarsoftware/octobot-trading-exchanges";
import { TraderOrderType } from "@drakkarsoftware/octobot-trading-exchanges";
import { createTradingKeywords } from "../src/trading.js";

function makeExchange(overrides: Partial<Record<string, unknown>> = {}): AbstractExchange {
  return {
    createOrder: vi.fn().mockResolvedValue({ id: "ord1" }),
    cancelOrder: vi.fn().mockResolvedValue("canceled"),
    getOpenOrders: vi.fn().mockResolvedValue([]),
    getOrder: vi.fn().mockResolvedValue({ id: "ord1" }),
    getBalance: vi.fn().mockResolvedValue({}),
    getMyRecentTrades: vi.fn().mockResolvedValue([]),
    ...overrides,
  } as unknown as AbstractExchange;
}

describe("createTradingKeywords", () => {
  describe("market", () => {
    it("buy places BUY_MARKET order with Decimal qty", async () => {
      const exchange = makeExchange();
      const kw = createTradingKeywords(exchange);
      const result = await kw.market("buy", "BTC/USDT", 20);
      expect(exchange.createOrder).toHaveBeenCalledWith(TraderOrderType.BUY_MARKET, "BTC/USDT", new Decimal(20));
      expect(result).toEqual({ id: "ord1" });
    });

    it("sell places SELL_MARKET order", async () => {
      const exchange = makeExchange();
      const kw = createTradingKeywords(exchange);
      await kw.market("sell", "BTC/USDT", "0.5");
      expect(exchange.createOrder).toHaveBeenCalledWith(TraderOrderType.SELL_MARKET, "BTC/USDT", new Decimal("0.5"));
    });

    it("accepts Decimal qty", async () => {
      const exchange = makeExchange();
      const kw = createTradingKeywords(exchange);
      await kw.market("buy", "ETH/USDT", new Decimal("1.5"));
      const [, , qty] = (exchange.createOrder as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(qty).toBeInstanceOf(Decimal);
      expect(qty.toNumber()).toBe(1.5);
    });
  });

  describe("limit", () => {
    it("buy places BUY_LIMIT with qty and price", async () => {
      const exchange = makeExchange();
      const kw = createTradingKeywords(exchange);
      await kw.limit("buy", "BTC/USDT", 10, 60000);
      expect(exchange.createOrder).toHaveBeenCalledWith(
        TraderOrderType.BUY_LIMIT,
        "BTC/USDT",
        new Decimal(10),
        new Decimal(60000),
      );
    });

    it("sell places SELL_LIMIT", async () => {
      const exchange = makeExchange();
      const kw = createTradingKeywords(exchange);
      await kw.limit("sell", "BTC/USDT", 5, "55000");
      expect(exchange.createOrder).toHaveBeenCalledWith(
        TraderOrderType.SELL_LIMIT,
        "BTC/USDT",
        new Decimal(5),
        new Decimal("55000"),
      );
    });
  });

  describe("cancel_order", () => {
    it("cancels every open order for the symbol and returns ids", async () => {
      const exchange = makeExchange({
        getOpenOrders: vi.fn().mockResolvedValue([
          { id: "o1", symbol: "BTC/USDT" },
          { id: "o2", symbol: "BTC/USDT" },
        ]),
        cancelOrder: vi.fn().mockResolvedValue("canceled"),
      });
      const kw = createTradingKeywords(exchange);
      const ids = await kw.cancel_order("BTC/USDT");
      expect(exchange.getOpenOrders).toHaveBeenCalledWith("BTC/USDT");
      expect(exchange.cancelOrder).toHaveBeenCalledTimes(2);
      expect(ids).toEqual(["o1", "o2"]);
    });

    it("returns empty array when no open orders and does not call cancelOrder", async () => {
      const exchange = makeExchange({ getOpenOrders: vi.fn().mockResolvedValue([]) });
      const kw = createTradingKeywords(exchange);
      const ids = await kw.cancel_order("BTC/USDT");
      expect(ids).toHaveLength(0);
      expect(exchange.cancelOrder).not.toHaveBeenCalled();
    });
  });

  describe("fetch_order", () => {
    it("delegates to getOrder with id and symbol", async () => {
      const exchange = makeExchange({ getOrder: vi.fn().mockResolvedValue({ id: "x", status: "open" }) });
      const kw = createTradingKeywords(exchange);
      const order = await kw.fetch_order("x", "ETH/USDT");
      expect(exchange.getOrder).toHaveBeenCalledWith("x", "ETH/USDT");
      expect(order).toEqual({ id: "x", status: "open" });
    });
  });

  describe("fetch_trades", () => {
    it("returns personal trade history for a symbol", async () => {
      const trades = [{ id: "t1", amount: 0.5 }];
      const exchange = makeExchange({ getMyRecentTrades: vi.fn().mockResolvedValue(trades) });
      const kw = createTradingKeywords(exchange);
      const result = await kw.fetch_trades("BTC/USDT");
      expect(exchange.getMyRecentTrades).toHaveBeenCalledWith("BTC/USDT", undefined, undefined);
      expect(result).toEqual(trades);
    });

    it("passes limit to getMyRecentTrades", async () => {
      const exchange = makeExchange({ getMyRecentTrades: vi.fn().mockResolvedValue([]) });
      const kw = createTradingKeywords(exchange);
      await kw.fetch_trades("BTC/USDT", 10);
      expect(exchange.getMyRecentTrades).toHaveBeenCalledWith("BTC/USDT", undefined, 10);
    });

    it("fetches without symbol when omitted", async () => {
      const exchange = makeExchange({ getMyRecentTrades: vi.fn().mockResolvedValue([]) });
      const kw = createTradingKeywords(exchange);
      await kw.fetch_trades();
      expect(exchange.getMyRecentTrades).toHaveBeenCalledWith(undefined, undefined, undefined);
    });
  });

  describe("total", () => {
    it("returns total balance Decimal for the asset", async () => {
      const exchange = makeExchange({
        getBalance: vi.fn().mockResolvedValue({ BTC: { total: new Decimal("0.5"), available: new Decimal("0.3") } }),
      });
      const kw = createTradingKeywords(exchange);
      expect((await kw.total("BTC")).toNumber()).toBe(0.5);
    });

    it("returns Decimal(0) when asset absent", async () => {
      const exchange = makeExchange({ getBalance: vi.fn().mockResolvedValue({}) });
      const kw = createTradingKeywords(exchange);
      expect((await kw.total("XRP")).toNumber()).toBe(0);
    });
  });

  describe("available", () => {
    it("returns available balance Decimal for the asset", async () => {
      const exchange = makeExchange({
        getBalance: vi.fn().mockResolvedValue({ BTC: { total: new Decimal("1"), available: new Decimal("0.7") } }),
      });
      const kw = createTradingKeywords(exchange);
      expect((await kw.available("BTC")).toNumber()).toBe(0.7);
    });

    it("returns Decimal(0) when asset absent", async () => {
      const exchange = makeExchange({ getBalance: vi.fn().mockResolvedValue({}) });
      const kw = createTradingKeywords(exchange);
      expect((await kw.available("ETH")).toNumber()).toBe(0);
    });
  });
});
