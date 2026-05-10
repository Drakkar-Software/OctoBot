import { describe, it, expect, vi, beforeEach } from "vitest";
import { TaskStatus, AccountType } from "@drakkarsoftware/octobot-protocol";
import type { Account, RemoveExchangeAccountAction } from "@drakkarsoftware/octobot-protocol";
import { emptyState } from "../../../src/state.js";
import type { AutomationContext } from "../../../src/runner.js";

const { mockStop } = vi.hoisted(() => {
  const mockStop = vi.fn().mockResolvedValue(undefined);
  return { mockStop };
});

vi.mock("@drakkarsoftware/octobot-trading", () => ({
  ExchangeBuilder: vi.fn(),
}));

import { createRemoveExchangeAccountHandler } from "../../../src/actions/handlers/trading/removeExchangeAccount.js";

function makeAction(accountId: string): RemoveExchangeAccountAction {
  return { id: "a1", actionType: "remove_exchange_account", status: TaskStatus.Pending, accountId };
}

function makeAccount(id: string): Account {
  return { id, accountType: AccountType.Exchange, name: id, isSimulated: false };
}

describe("createRemoveExchangeAccountHandler", () => {
  let registry: Map<string, { stop: typeof mockStop; id: string }>;

  beforeEach(() => {
    registry = new Map();
    mockStop.mockClear();
  });

  it("stops manager in registry, removes it, stages removal, returns accountId", async () => {
    const manager = { stop: mockStop, id: "mgr-1" };
    registry.set("acc1", manager);

    const handler = createRemoveExchangeAccountHandler(registry as never);
    const removeAccount = vi.fn();
    const ctx = { removeAccount } as unknown as AutomationContext;

    const result = await handler(makeAction("acc1"), ctx, emptyState());

    expect(mockStop).toHaveBeenCalledOnce();
    expect(registry.has("acc1")).toBe(false);
    expect(removeAccount).toHaveBeenCalledWith("acc1");
    expect(result).toEqual({ accountId: "acc1" });
  });

  it("stages removal even when accountId not in registry", async () => {
    const handler = createRemoveExchangeAccountHandler(registry as never);
    const removeAccount = vi.fn();

    await handler(makeAction("ghost"), { removeAccount } as unknown as AutomationContext, emptyState());

    expect(mockStop).not.toHaveBeenCalled();
    expect(removeAccount).toHaveBeenCalledWith("ghost");
  });

  it("is a no-op when ctx.removeAccount is absent", async () => {
    const handler = createRemoveExchangeAccountHandler(registry as never);
    await expect(handler(makeAction("acc1"), {} as AutomationContext, emptyState())).resolves.not.toThrow();
  });

  it("workflow: pre-seeded account removed from accountsState", async () => {
    const { AutomationWorkflow } = await import("../../../src/workflow.js");
    const { sendActionsToAutomation } = await import("../../../src/dispatch.js");
    const { emptyState: es } = await import("../../../src/state.js");
    const { emptyAccountsState, replaceAccount } = await import("../../../src/accounts.js");

    const handler = createRemoveExchangeAccountHandler(registry as never);
    const seeded = replaceAccount(emptyAccountsState(), makeAccount("acc-to-remove"));
    const wf = new AutomationWorkflow();
    const out = await wf.executeAutomation({
      automation: { id: "auto1", metadata: { name: "t", description: "" }, run: async () => ({}) },
      state: es(),
      accountsState: seeded,
      reason: "test",
      envelopes: [sendActionsToAutomation("auto1", [makeAction("acc-to-remove")])],
      actionHandlers: { remove_exchange_account: handler },
    });

    expect(out.accountsState.accounts).toHaveLength(0);
    expect(out.actionExecutions[0].status).toBe(TaskStatus.Completed);
  });

  it("workflow: removing absent accountId is a no-op (state unchanged)", async () => {
    const { AutomationWorkflow } = await import("../../../src/workflow.js");
    const { sendActionsToAutomation } = await import("../../../src/dispatch.js");
    const { emptyState: es } = await import("../../../src/state.js");
    const { emptyAccountsState, replaceAccount } = await import("../../../src/accounts.js");

    const handler = createRemoveExchangeAccountHandler(registry as never);
    const seeded = replaceAccount(emptyAccountsState(), makeAccount("other"));
    const wf = new AutomationWorkflow();
    const out = await wf.executeAutomation({
      automation: { id: "auto1", metadata: { name: "t", description: "" }, run: async () => ({}) },
      state: es(),
      accountsState: seeded,
      reason: "test",
      envelopes: [sendActionsToAutomation("auto1", [makeAction("nonexistent")])],
      actionHandlers: { remove_exchange_account: handler },
    });

    expect(out.accountsState.accounts).toHaveLength(1);
    expect(out.actionExecutions[0].status).toBe(TaskStatus.Completed);
  });
});
