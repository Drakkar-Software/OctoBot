import { describe, it, expect, vi } from "vitest";
import { TaskStatus, AccountType } from "@drakkarsoftware/octobot-protocol";
import type { Account, RemoveExchangeAccountAction } from "@drakkarsoftware/octobot-protocol";
import { removeExchangeAccountHandler } from "../../../src/actions/handlers/index.js";
import { emptyState } from "../../../src/state.js";
import type { AutomationContext } from "../../../src/runner.js";

function makeAction(accountId: string): RemoveExchangeAccountAction {
  return { id: "a1", actionType: "remove_exchange_account", status: TaskStatus.Pending, accountId };
}

function makeAccount(id: string): Account {
  return { id, accountType: AccountType.Exchange, name: id, isSimulated: false };
}

describe("removeExchangeAccountHandler", () => {
  it("calls ctx.removeAccount with the accountId and returns it", async () => {
    const removeAccount = vi.fn();
    const ctx = { removeAccount } as unknown as AutomationContext;

    const result = await removeExchangeAccountHandler(makeAction("acc1"), ctx, emptyState());

    expect(removeAccount).toHaveBeenCalledOnce();
    expect(removeAccount).toHaveBeenCalledWith("acc1");
    expect(result).toEqual({ accountId: "acc1" });
  });

  it("is a no-op (Completed) when ctx.removeAccount is absent", async () => {
    const ctx = {} as AutomationContext;
    await expect(removeExchangeAccountHandler(makeAction("acc1"), ctx, emptyState())).resolves.not.toThrow();
  });

  it("workflow: pre-seeded account is removed from accountsState after action executes", async () => {
    const { AutomationWorkflow } = await import("../../../src/workflow.js");
    const { sendActionsToAutomation } = await import("../../../src/dispatch.js");
    const { emptyState: es } = await import("../../../src/state.js");
    const { emptyAccountsState, replaceAccount } = await import("../../../src/accounts.js");

    const seeded = replaceAccount(emptyAccountsState(), makeAccount("acc-to-remove"));
    const wf = new AutomationWorkflow();
    const out = await wf.executeAutomation({
      automation: { id: "auto1", metadata: { name: "t", description: "" }, run: async () => ({}) },
      state: es(),
      accountsState: seeded,
      reason: "test",
      envelopes: [
        sendActionsToAutomation("auto1", [makeAction("acc-to-remove")]),
      ],
      actionHandlers: { remove_exchange_account: removeExchangeAccountHandler },
    });

    expect(out.accountsState.accounts).toHaveLength(0);
    expect(out.actionExecutions[0].status).toBe(TaskStatus.Completed);
  });

  it("workflow: removing absent accountId is a no-op (account list unchanged)", async () => {
    const { AutomationWorkflow } = await import("../../../src/workflow.js");
    const { sendActionsToAutomation } = await import("../../../src/dispatch.js");
    const { emptyState: es } = await import("../../../src/state.js");
    const { emptyAccountsState, replaceAccount } = await import("../../../src/accounts.js");

    const seeded = replaceAccount(emptyAccountsState(), makeAccount("other"));
    const wf = new AutomationWorkflow();
    const out = await wf.executeAutomation({
      automation: { id: "auto1", metadata: { name: "t", description: "" }, run: async () => ({}) },
      state: es(),
      accountsState: seeded,
      reason: "test",
      envelopes: [
        sendActionsToAutomation("auto1", [makeAction("nonexistent")]),
      ],
      actionHandlers: { remove_exchange_account: removeExchangeAccountHandler },
    });

    expect(out.accountsState.accounts).toHaveLength(1);
    expect(out.actionExecutions[0].status).toBe(TaskStatus.Completed);
  });
});
