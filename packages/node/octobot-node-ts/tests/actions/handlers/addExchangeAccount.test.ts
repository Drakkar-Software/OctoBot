import { describe, it, expect, vi, beforeEach } from "vitest";
import { TaskStatus, AccountType } from "@drakkarsoftware/octobot-protocol";
import type { Account, AddExchangeAccountAction } from "@drakkarsoftware/octobot-protocol";
import { InvalidAccountError } from "../../../src/errors.js";
import { emptyState } from "../../../src/state.js";
import { emptyAccountsState } from "../../../src/accounts.js";
import type { AutomationContext } from "../../../src/runner.js";

const { mockStop, mockBuild, mockSetCredentials, mockManager } = vi.hoisted(() => {
  const mockStop = vi.fn().mockResolvedValue(undefined);
  const mockManager = { stop: mockStop, id: "mock-manager-id" };
  const mockBuild = vi.fn().mockReturnValue(mockManager);
  const mockSetCredentials = vi.fn();
  return { mockStop, mockBuild, mockSetCredentials, mockManager };
});

vi.mock("@drakkarsoftware/octobot-trading", () => ({
  ExchangeBuilder: vi.fn().mockImplementation(() => ({
    setCredentials: mockSetCredentials.mockReturnThis(),
    build: mockBuild,
  })),
}));

import { createAddExchangeAccountHandler } from "../../../src/actions/handlers/trading/addExchangeAccount.js";

function makeAccount(overrides: Partial<Account> = {}): Account {
  return {
    id: "acc1",
    accountType: AccountType.Exchange,
    name: "acc1",
    isSimulated: false,
    exchangeAccount: {
      exchange: "binance",
      remoteAccountId: "remote-1",
      apiKey: "key",
      apiSecret: "secret",
    },
    ...overrides,
  };
}

function makeAction(account: Account): AddExchangeAccountAction {
  return { id: "a1", actionType: "add_exchange_account", status: TaskStatus.Pending, account };
}

describe("createAddExchangeAccountHandler", () => {
  let registry: Map<string, ReturnType<typeof mockBuild>>;

  beforeEach(() => {
    registry = new Map();
    mockStop.mockClear();
    mockBuild.mockClear();
    mockSetCredentials.mockClear();
  });

  it("builds ExchangeManager, stores in registry, stages account, returns it", async () => {
    const handler = createAddExchangeAccountHandler(registry as never);
    const account = makeAccount();
    const replaceAccount = vi.fn();
    const ctx = { replaceAccount } as unknown as AutomationContext;

    const result = await handler(makeAction(account), ctx, emptyState());

    expect(mockBuild).toHaveBeenCalledOnce();
    expect(mockSetCredentials).toHaveBeenCalledWith({ apiKey: "key", secret: "secret", password: undefined });
    expect(registry.get("acc1")).toBe(mockManager);
    expect(replaceAccount).toHaveBeenCalledWith(account);
    expect(result).toBe(account);
  });

  it("stops existing manager before replacing", async () => {
    const handler = createAddExchangeAccountHandler(registry as never);
    const oldManager = { stop: vi.fn().mockResolvedValue(undefined), id: "old" };
    registry.set("acc1", oldManager as never);

    await handler(makeAction(makeAccount()), { replaceAccount: vi.fn() } as unknown as AutomationContext, emptyState());

    expect(oldManager.stop).toHaveBeenCalledOnce();
    expect(registry.get("acc1")).toBe(mockManager);
  });

  it("simulated account: skips ExchangeManager, stages account", async () => {
    const handler = createAddExchangeAccountHandler(registry as never);
    const account = makeAccount({ isSimulated: true });
    const replaceAccount = vi.fn();

    await handler(makeAction(account), { replaceAccount } as unknown as AutomationContext, emptyState());

    expect(mockBuild).not.toHaveBeenCalled();
    expect(registry.size).toBe(0);
    expect(replaceAccount).toHaveBeenCalledWith(account);
  });

  it("throws InvalidAccountError for non-Exchange account type", async () => {
    const handler = createAddExchangeAccountHandler(registry as never);
    const account = makeAccount({ accountType: AccountType.Generic });
    const ctx = {} as AutomationContext;

    await expect(handler(makeAction(account), ctx, emptyState())).rejects.toThrow(InvalidAccountError);
  });

  it("throws InvalidAccountError when exchange name is missing", async () => {
    const handler = createAddExchangeAccountHandler(registry as never);
    const account = makeAccount({ exchangeAccount: { exchange: "", remoteAccountId: "", apiKey: "k", apiSecret: "s" } });
    await expect(handler(makeAction(account), {} as AutomationContext, emptyState())).rejects.toThrow(InvalidAccountError);
  });

  it("throws InvalidAccountError when live account has no apiKey", async () => {
    const handler = createAddExchangeAccountHandler(registry as never);
    const account = makeAccount({ exchangeAccount: { exchange: "binance", remoteAccountId: "", apiKey: "", apiSecret: "" } });
    await expect(handler(makeAction(account), {} as AutomationContext, emptyState())).rejects.toThrow(InvalidAccountError);
  });

  it("workflow: account appears in accountsState after action executes", async () => {
    const { AutomationWorkflow } = await import("../../../src/workflow.js");
    const { sendActionsToAutomation } = await import("../../../src/dispatch.js");
    const { emptyState: es } = await import("../../../src/state.js");
    const { emptyAccountsState: eas } = await import("../../../src/accounts.js");

    const handler = createAddExchangeAccountHandler(registry as never);
    const account = makeAccount({ id: "acx" });
    const wf = new AutomationWorkflow();
    const out = await wf.executeAutomation({
      automation: { id: "auto1", metadata: { name: "t", description: "" }, run: async () => ({}) },
      state: es(),
      accountsState: eas(),
      reason: "test",
      envelopes: [sendActionsToAutomation("auto1", [makeAction(account)])],
      actionHandlers: { add_exchange_account: handler },
    });

    expect(out.accountsState.accounts).toHaveLength(1);
    expect(out.accountsState.accounts?.[0].id).toBe("acx");
    expect(out.actionExecutions[0].status).toBe(TaskStatus.Completed);
  });
});
