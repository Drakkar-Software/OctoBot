import { describe, it, expect, vi } from "vitest";
import { TaskStatus } from "@drakkarsoftware/octobot-protocol";
import type { AbstractExchange } from "@drakkarsoftware/octobot-flow";
import { TraderOrderType } from "@drakkarsoftware/octobot-flow";
import { createDslActionHandler, createFlowActionHandlers } from "../../src/dsl/handler.js";
import { DslParseError, DslKeywordMismatchError } from "../../src/errors.js";
import type { Action } from "@drakkarsoftware/octobot-protocol";

function mkAction(actionType: string, dsl?: string): Action {
  return { id: "a1", actionType, status: TaskStatus.Pending, dsl };
}

function makeExchange(overrides: Partial<Record<string, unknown>> = {}): AbstractExchange {
  return {
    createOrder: vi.fn().mockResolvedValue({ id: "ord1" }),
    cancelOrder: vi.fn().mockResolvedValue("canceled"),
    getOpenOrders: vi.fn().mockResolvedValue([]),
    getOrder: vi.fn().mockResolvedValue({ id: "ord1" }),
    getBalance: vi.fn().mockResolvedValue({}),
    getMyRecentTrades: vi.fn().mockResolvedValue([]),
    getKlinePrice: vi.fn().mockResolvedValue([0, 0, 0, 0, 0, 0]),
    getPriceTicker: vi.fn().mockResolvedValue({}),
    getOrderBook: vi.fn().mockResolvedValue({ bids: [], asks: [] }),
    ...overrides,
  } as unknown as AbstractExchange;
}

describe("createDslActionHandler", () => {
  it("calls the bound keyword with parsed args and returns its result", async () => {
    const keyword = vi.fn().mockResolvedValue("ok");
    const handler = createDslActionHandler(keyword);
    const result = await handler(mkAction("market", "market(buy, BTC/USDT, 0.1)"), {} as any, {} as any);
    expect(keyword).toHaveBeenCalledWith("buy", "BTC/USDT", 0.1);
    expect(result).toBe("ok");
  });

  it("throws DslKeywordMismatchError when actionType does not match parsed keyword", async () => {
    const keyword = vi.fn();
    const handler = createDslActionHandler(keyword);
    await expect(
      handler(mkAction("market", "limit(buy, BTC/USDT, 1, 60000)"), {} as any, {} as any),
    ).rejects.toThrow(DslKeywordMismatchError);
    expect(keyword).not.toHaveBeenCalled();
  });

  it("throws DslParseError when action.dsl is absent", async () => {
    const keyword = vi.fn();
    const handler = createDslActionHandler(keyword);
    await expect(handler(mkAction("market", undefined), {} as any, {} as any)).rejects.toThrow(DslParseError);
  });

  it("returns keyword result verbatim", async () => {
    const payload = { id: "ord1", status: "open" };
    const keyword = vi.fn().mockResolvedValue(payload);
    const handler = createDslActionHandler(keyword);
    const result = await handler(mkAction("market", "market(buy, BTC/USDT, 1)"), {} as any, {} as any);
    expect(result).toBe(payload);
  });
});

describe("createFlowActionHandlers", () => {
  it("returns handlers for every flow keyword", () => {
    const handlers = createFlowActionHandlers(makeExchange());
    const expectedKeys = [
      "market", "limit", "cancel_order", "fetch_order", "fetch_trades", "total", "available",
      "close", "open", "high", "low", "volume", "time",
      "ticker_last", "ticker_close", "ticker_open", "ticker_high", "ticker_low", "ticker_volume",
      "bid", "ask", "bid_volume", "ask_volume",
    ];
    for (const key of expectedKeys) {
      expect(handlers[key], `missing handler for "${key}"`).toBeTypeOf("function");
    }
  });

  it("market handler dispatches to createOrder with correct types", async () => {
    const exchange = makeExchange();
    const handlers = createFlowActionHandlers(exchange);
    await handlers["market"](mkAction("market", "market(buy, BTC/USDT, 0.1)"), {} as any, {} as any);
    const [orderType, symbol, qty] = (exchange.createOrder as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(orderType).toBe(TraderOrderType.BUY_MARKET);
    expect(symbol).toBe("BTC/USDT");
    expect(qty.toNumber()).toBe(0.1);
  });
});
