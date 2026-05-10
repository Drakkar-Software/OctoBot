import { describe, it, expect, vi } from "vitest";
import { TaskStatus, AccountType } from "@drakkarsoftware/octobot-protocol";
import type { Account, AutomationState } from "@drakkarsoftware/octobot-protocol";
import { OctobotNode } from "../../../src/node.js";
import { emptyState, replaceAutomationRow } from "../../../src/state.js";
import { emptyAccountsState, replaceAccount } from "../../../src/accounts.js";
import { sendActionsToAutomation } from "../../../src/dispatch.js";
import { defaultActionHandlers } from "../../../src/actions/handlers/index.js";
import { createTradingHandlers } from "../../../src/actions/handlers/trading/index.js";
import type { Automation } from "../../../src/runner.js";

vi.mock("@drakkarsoftware/octobot-trading", () => ({
  ExchangeBuilder: vi.fn(),
}));

// Simulated exchange accounts skip ExchangeManager creation — no mocking of ExchangeBuilder needed.
function mkAccount(id: string): Account {
  return {
    id,
    accountType: AccountType.Exchange,
    name: id,
    isSimulated: true,
    exchangeAccount: { exchange: "binance", remoteAccountId: "", apiKey: "", apiSecret: "" },
  };
}

function mkAutomationRow(id: string): AutomationState {
  return { id, status: TaskStatus.Pending, metadata: { name: id, description: "" } };
}

const noopAutomation: Automation = {
  id: "main",
  metadata: { name: "main", description: "" },
  run: async () => ({}),
};

describe("defaultActionHandlers e2e via OctobotNode.run", () => {
  it("all 4 actions applied sequentially in a single run; each subsequent action sees prior mutations", async () => {
    const node = new OctobotNode();
    const registry = new Map();

    const existingAccount = mkAccount("old-account");
    const newAccount = mkAccount("new-account");
    const existingBot = mkAutomationRow("old-bot");
    const newBot = mkAutomationRow("new-bot");

    const initialState = replaceAutomationRow(emptyState(), existingBot);
    const initialAccounts = replaceAccount(emptyAccountsState(), existingAccount);
    const actionHandlers = { ...defaultActionHandlers, ...createTradingHandlers(registry) };

    const result = await node.run({
      automations: [noopAutomation],
      state: initialState,
      reason: "test",
      accountsState: initialAccounts,
      actionHandlers,
      envelopes: [
        sendActionsToAutomation("main", [
          { id: "act1", actionType: "add_exchange_account", status: TaskStatus.Pending, account: newAccount },
          { id: "act2", actionType: "remove_exchange_account", status: TaskStatus.Pending, accountId: "old-account" },
          { id: "act3", actionType: "add_automation", status: TaskStatus.Pending, automation: newBot },
          { id: "act4", actionType: "remove_automation", status: TaskStatus.Pending, automationId: "old-bot" },
        ]),
      ],
    });

    const accountIds = result.nextAccountsState.accounts?.map((a) => a.id) ?? [];
    expect(accountIds).toContain("new-account");
    expect(accountIds).not.toContain("old-account");

    const botIds = result.nextState.automations?.map((a) => a.id) ?? [];
    expect(botIds).toContain("new-bot");
    expect(botIds).not.toContain("old-bot");

    expect(result.resolvedActions).toHaveLength(4);
    for (const action of result.resolvedActions) {
      expect(action.status).toBe(TaskStatus.Completed);
    }
  });
});
