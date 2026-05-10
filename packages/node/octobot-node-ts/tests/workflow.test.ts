import { describe, it, expect, vi } from "vitest";
import { AutomationWorkflow } from "../src/workflow.js";
import { emptyState } from "../src/state.js";
import { emptyAccountsState, replaceAccount } from "../src/accounts.js";
import {
  sendActionsToAutomation,
  triggerCopierAutomation,
  sendForcedTriggerToAutomation,
} from "../src/dispatch.js";
import { ActionHandlerNotFoundError } from "../src/errors.js";
import { TaskStatus, AccountType } from "@drakkarsoftware/octobot-protocol";
import type { Account, Action, AutomationsState } from "@drakkarsoftware/octobot-protocol";
import type { Automation } from "../src/runner.js";
import type { ActionHandler } from "../src/actions.js";

const meta = (name: string) => ({ name, description: "" });

const mkAccount = (id: string, balance = 100): Account => ({
  id,
  accountType: AccountType.Exchange,
  name: id,
  isSimulated: false,
  exchangeAccount: {
    exchange: "binance",
    remoteAccountId: id,
    apiKey: "k",
    apiSecret: "s",
    assets: [{ symbol: "USDT", total: balance, available: balance }],
  },
});

const mkAction = (id: string, actionType: string): Action => ({
  id,
  actionType,
  status: TaskStatus.Pending,
});

const noopAutomation = (id: string): Automation => ({
  id,
  metadata: meta(id),
  run: async () => ({ from: id }),
});

describe("AutomationWorkflow.executeAutomation", () => {
  it("happy path: no envelopes — main automation runs, empty action outputs", async () => {
    const wf = new AutomationWorkflow();
    const out = await wf.executeAutomation({
      automation: noopAutomation("a1"),
      state: emptyState(),
      reason: "test",
    });
    expect(out.execution.automationId).toBe("a1");
    expect(out.execution.status).toBe(TaskStatus.Completed);
    expect(out.actionExecutions).toHaveLength(0);
    expect(out.resolvedActions).toHaveLength(0);
    expect(out.accountsState.accounts).toHaveLength(0);
  });

  it("USER_ACTIONS: account-sync handler calls ctx.replaceAccount; main automation sees refreshed balance", async () => {
    const wf = new AutomationWorkflow();
    const initialAccount = mkAccount("acc1", 100);
    const refreshedAccount = mkAccount("acc1", 200);
    let observedBalance: number | undefined;

    const automation: Automation = {
      id: "a1",
      metadata: meta("a1"),
      run: async (ctx) => {
        observedBalance = (ctx.accounts?.accounts?.[0]?.exchangeAccount?.assets?.[0]?.total as number);
        return {};
      },
    };

    const syncHandler: ActionHandler = async (_action, ctx) => {
      ctx.replaceAccount!(refreshedAccount);
      return { ok: true };
    };

    const out = await wf.executeAutomation({
      automation,
      state: emptyState(),
      accountsState: { ...emptyAccountsState(), accounts: [initialAccount] },
      reason: "test",
      envelopes: [sendActionsToAutomation("a1", [mkAction("act1", "account-sync")])],
      actionHandlers: { "account-sync": syncHandler },
    });

    expect(observedBalance).toBe(200);
    expect(out.accountsState.accounts?.[0]?.exchangeAccount?.assets?.[0]?.total).toBe(200);
    expect(out.actionExecutions).toHaveLength(1);
    expect(out.actionExecutions[0].status).toBe(TaskStatus.Completed);
    expect(out.resolvedActions[0].status).toBe(TaskStatus.Completed);
  });

  it("USER_ACTIONS: multiple actions execute in order; later actions see earlier replacements", async () => {
    const wf = new AutomationWorkflow();
    const balanceSeen: number[] = [];

    const handler: ActionHandler = async (_action, ctx) => {
      const balance = ctx.accounts?.accounts?.[0]?.exchangeAccount?.assets?.[0]?.total as number ?? 0;
      balanceSeen.push(balance);
      ctx.replaceAccount!(mkAccount("acc1", balance + 50));
      return {};
    };

    const out = await wf.executeAutomation({
      automation: noopAutomation("a1"),
      state: emptyState(),
      accountsState: { ...emptyAccountsState(), accounts: [mkAccount("acc1", 100)] },
      reason: "test",
      envelopes: [
        sendActionsToAutomation("a1", [mkAction("act1", "add"), mkAction("act2", "add")]),
      ],
      actionHandlers: { add: handler },
    });

    expect(balanceSeen).toEqual([100, 150]);
    expect(out.accountsState.accounts?.[0]?.exchangeAccount?.assets?.[0]?.total).toBe(200);
    expect(out.actionExecutions).toHaveLength(2);
  });

  it("TRADING_SIGNAL: main automation observes ctx.tradingSignals", async () => {
    const wf = new AutomationWorkflow();
    let observed: unknown[] | undefined;

    const automation: Automation = {
      id: "a1",
      metadata: meta("a1"),
      run: async (ctx) => { observed = ctx.tradingSignals; return {}; },
    };

    const signals = [{ type: "buy", amount: 1 }];
    await wf.executeAutomation({
      automation,
      state: emptyState(),
      reason: "test",
      envelopes: [triggerCopierAutomation("a1", signals)],
    });

    expect(observed).toEqual(signals);
  });

  it("FORCED_TRIGGER: ctx.forced is true; automation with shouldRun=false still runs", async () => {
    const wf = new AutomationWorkflow();
    let ran = false;
    let observedForced: boolean | undefined;

    const automation: Automation = {
      id: "a1",
      metadata: meta("a1"),
      shouldRun: () => false,
      run: async (ctx) => { ran = true; observedForced = ctx.forced; return {}; },
    };

    const out = await wf.executeAutomation({
      automation,
      state: emptyState(),
      reason: "test",
      envelopes: [sendForcedTriggerToAutomation("a1")],
    });

    expect(ran).toBe(true);
    expect(observedForced).toBe(true);
    expect(out.execution.status).toBe(TaskStatus.Completed);
  });

  it("mixed envelopes for the same automationId all merge correctly", async () => {
    const wf = new AutomationWorkflow();
    let forced = false;
    let signals: unknown[] | undefined;

    const handler: ActionHandler = async () => ({});

    const automation: Automation = {
      id: "a1",
      metadata: meta("a1"),
      shouldRun: () => false,
      run: async (ctx) => { forced = ctx.forced ?? false; signals = ctx.tradingSignals; return {}; },
    };

    const out = await wf.executeAutomation({
      automation,
      state: emptyState(),
      reason: "test",
      envelopes: [
        sendActionsToAutomation("a1", [mkAction("act1", "noop")]),
        triggerCopierAutomation("a1", [{ type: "sell" }]),
        sendForcedTriggerToAutomation("a1"),
      ],
      actionHandlers: { noop: handler },
    });

    expect(forced).toBe(true);
    expect(signals).toEqual([{ type: "sell" }]);
    expect(out.actionExecutions).toHaveLength(1);
    expect(out.execution.status).toBe(TaskStatus.Completed);
  });

  it("envelopes for a different automationId are ignored", async () => {
    const wf = new AutomationWorkflow();
    let ran = false;

    const handler: ActionHandler = async () => { ran = true; return {}; };

    await wf.executeAutomation({
      automation: noopAutomation("a1"),
      state: emptyState(),
      reason: "test",
      envelopes: [sendActionsToAutomation("OTHER", [mkAction("act1", "noop")])],
      actionHandlers: { noop: handler },
    });

    expect(ran).toBe(false);
  });

  it("missing handler throws ActionHandlerNotFoundError before running anything", async () => {
    const wf = new AutomationWorkflow();
    let mainRan = false;

    const automation: Automation = {
      id: "a1",
      metadata: meta("a1"),
      run: async () => { mainRan = true; return {}; },
    };

    await expect(
      wf.executeAutomation({
        automation,
        state: emptyState(),
        reason: "test",
        envelopes: [sendActionsToAutomation("a1", [mkAction("act1", "missing-type")])],
        actionHandlers: {},
      }),
    ).rejects.toThrow(ActionHandlerNotFoundError);

    expect(mainRan).toBe(false);
  });

  it("signal aborted before call → actions skipped (no executions), main automation Cancelled", async () => {
    const wf = new AutomationWorkflow();
    const ctrl = new AbortController();
    ctrl.abort();

    const handler: ActionHandler = async () => ({});
    const out = await wf.executeAutomation({
      automation: noopAutomation("a1"),
      state: emptyState(),
      reason: "test",
      envelopes: [sendActionsToAutomation("a1", [mkAction("act1", "noop")])],
      actionHandlers: { noop: handler },
      signal: ctrl.signal,
    });

    // Actions never start — loop breaks immediately on aborted signal.
    expect(out.actionExecutions).toHaveLength(0);
    expect(out.execution.status).toBe(TaskStatus.Cancelled);
  });

  it("one failing action does not block subsequent actions nor the main automation", async () => {
    const wf = new AutomationWorkflow();
    let mainRan = false;

    const failHandler: ActionHandler = async () => { throw new Error("boom"); };
    const okHandler: ActionHandler = async () => ({ ok: true });

    const out = await wf.executeAutomation({
      automation: {
        id: "a1",
        metadata: meta("a1"),
        run: async () => { mainRan = true; return {}; },
      },
      state: emptyState(),
      reason: "test",
      envelopes: [
        sendActionsToAutomation("a1", [mkAction("act1", "fail"), mkAction("act2", "ok")]),
      ],
      actionHandlers: { fail: failHandler, ok: okHandler },
    });

    expect(out.actionExecutions[0].status).toBe(TaskStatus.Failed);
    expect(out.actionExecutions[0].error?.message).toBe("boom");
    expect(out.actionExecutions[1].status).toBe(TaskStatus.Completed);
    expect(mainRan).toBe(true);
    expect(out.execution.status).toBe(TaskStatus.Completed);
  });

  it("main automation throwing produces Failed execution; action executions still returned", async () => {
    const wf = new AutomationWorkflow();
    const handler: ActionHandler = async () => ({});

    const out = await wf.executeAutomation({
      automation: {
        id: "a1",
        metadata: meta("a1"),
        run: async () => { throw new Error("auto-fail"); },
      },
      state: emptyState(),
      reason: "test",
      envelopes: [sendActionsToAutomation("a1", [mkAction("act1", "noop")])],
      actionHandlers: { noop: handler },
    });

    expect(out.actionExecutions[0].status).toBe(TaskStatus.Completed);
    expect(out.execution.status).toBe(TaskStatus.Failed);
    expect(out.execution.error?.message).toBe("auto-fail");
  });
});
