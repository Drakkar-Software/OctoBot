import { describe, it, expect, vi } from "vitest";
import { TaskStatus } from "@drakkarsoftware/octobot-protocol";
import type { AbstractExchange } from "@drakkarsoftware/octobot-flow";
import { TraderOrderType } from "@drakkarsoftware/octobot-flow";
import { AutomationWorkflow } from "../../src/workflow.js";
import { emptyState } from "../../src/state.js";
import { sendActionsToAutomation } from "../../src/dispatch.js";
import { createFlowActionHandlers } from "../../src/dsl/handler.js";
import type { Automation } from "../../src/runner.js";

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

const noopAutomation: Automation = {
  id: "auto1",
  metadata: { name: "test", description: "" },
  run: async () => ({}),
};

describe("DSL integration via AutomationWorkflow", () => {
  it("executes market DSL action: exchange.createOrder called with correct args", async () => {
    const exchange = makeExchange();
    const handlers = createFlowActionHandlers(exchange);
    const wf = new AutomationWorkflow();

    const out = await wf.executeAutomation({
      automation: noopAutomation,
      state: emptyState(),
      reason: "tick",
      envelopes: [
        sendActionsToAutomation("auto1", [
          { id: "a1", actionType: "market", dsl: "market(buy, BTC/USDT, 20)", status: TaskStatus.Pending },
        ]),
      ],
      actionHandlers: handlers,
    });

    const [orderType, symbol, qty] = (exchange.createOrder as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(orderType).toBe(TraderOrderType.BUY_MARKET);
    expect(symbol).toBe("BTC/USDT");
    expect(qty.toNumber()).toBe(20);
    expect(out.actionExecutions).toHaveLength(1);
    expect(out.actionExecutions[0].status).toBe(TaskStatus.Completed);
  });

  it("keyword mismatch produces a Failed action execution", async () => {
    const exchange = makeExchange();
    const handlers = createFlowActionHandlers(exchange);
    const wf = new AutomationWorkflow();

    const out = await wf.executeAutomation({
      automation: noopAutomation,
      state: emptyState(),
      reason: "tick",
      envelopes: [
        sendActionsToAutomation("auto1", [
          { id: "a1", actionType: "market", dsl: "limit(buy, BTC/USDT, 1, 60000)", status: TaskStatus.Pending },
        ]),
      ],
      actionHandlers: handlers,
    });

    expect(out.actionExecutions[0].status).toBe(TaskStatus.Failed);
    expect(out.actionExecutions[0].error?.message).toMatch(/DslKeywordMismatchError|does not match/);
  });
});
