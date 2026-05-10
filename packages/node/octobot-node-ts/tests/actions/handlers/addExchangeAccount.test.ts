import { describe, it, expect, vi } from "vitest";
import { TaskStatus } from "@drakkarsoftware/octobot-protocol";
import type { Account, AddExchangeAccountAction } from "@drakkarsoftware/octobot-protocol";
import { AccountType } from "@drakkarsoftware/octobot-protocol";
import { addExchangeAccountHandler } from "../../../src/actions/handlers/index.js";
import { emptyAccountsState } from "../../../src/accounts.js";
import { emptyState } from "../../../src/state.js";
import type { AutomationContext } from "../../../src/runner.js";

function makeAccount(id = "acc1"): Account {
  return {
    id,
    accountType: AccountType.Exchange,
    name: id,
    isSimulated: false,
    exchangeAccount: {
      exchange: "binance",
      remoteAccountId: "remote-1",
      apiKey: "key",
      apiSecret: "secret",
    },
  };
}

function makeAction(account: Account): AddExchangeAccountAction {
  return {
    id: "a1",
    actionType: "add_exchange_account",
    status: TaskStatus.Pending,
    account,
  };
}

describe("addExchangeAccountHandler", () => {
  it("calls ctx.replaceAccount with the action account and returns it", async () => {
    const account = makeAccount();
    const action = makeAction(account);
    const replaceAccount = vi.fn();
    const ctx = { replaceAccount } as unknown as AutomationContext;

    const result = await addExchangeAccountHandler(action, ctx, emptyState());

    expect(replaceAccount).toHaveBeenCalledOnce();
    expect(replaceAccount).toHaveBeenCalledWith(account);
    expect(result).toBe(account);
  });

  it("is a no-op when ctx.replaceAccount is absent", async () => {
    const action = makeAction(makeAccount());
    const ctx = {} as AutomationContext;
    await expect(addExchangeAccountHandler(action, ctx, emptyState())).resolves.not.toThrow();
  });

  it("workflow: account appears in output accountsState after action executes", async () => {
    const { AutomationWorkflow } = await import("../../../src/workflow.js");
    const { sendActionsToAutomation } = await import("../../../src/dispatch.js");
    const { emptyState: es } = await import("../../../src/state.js");
    const { emptyAccountsState: eas } = await import("../../../src/accounts.js");

    const account = makeAccount("acx");
    const wf = new AutomationWorkflow();
    const out = await wf.executeAutomation({
      automation: { id: "auto1", metadata: { name: "t", description: "" }, run: async () => ({}) },
      state: es(),
      accountsState: eas(),
      reason: "test",
      envelopes: [
        sendActionsToAutomation("auto1", [makeAction(account)]),
      ],
      actionHandlers: { add_exchange_account: addExchangeAccountHandler },
    });

    expect(out.accountsState.accounts).toHaveLength(1);
    expect(out.accountsState.accounts?.[0].id).toBe("acx");
    expect(out.actionExecutions[0].status).toBe(TaskStatus.Completed);
  });
});
