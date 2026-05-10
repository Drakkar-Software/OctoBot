import { describe, it, expect, vi } from "vitest";
import { TaskStatus } from "@drakkarsoftware/octobot-protocol";
import type { RemoveAutomationAction, AutomationState } from "@drakkarsoftware/octobot-protocol";
import { removeAutomationHandler } from "../../../src/actions/handlers/index.js";
import { emptyState, replaceAutomationRow } from "../../../src/state.js";
import type { AutomationContext } from "../../../src/runner.js";

function makeAutomationRow(id: string): AutomationState {
  return { id, status: TaskStatus.Pending, metadata: { name: id, description: "" } };
}

function makeAction(automationId: string): RemoveAutomationAction {
  return { id: "a1", actionType: "remove_automation", status: TaskStatus.Pending, automationId };
}

describe("removeAutomationHandler", () => {
  it("calls ctx.removeAutomation with the automationId and returns it", async () => {
    const removeAutomation = vi.fn();
    const ctx = { removeAutomation } as unknown as AutomationContext;

    const result = await removeAutomationHandler(makeAction("bot1"), ctx, emptyState());

    expect(removeAutomation).toHaveBeenCalledOnce();
    expect(removeAutomation).toHaveBeenCalledWith("bot1");
    expect(result).toEqual({ automationId: "bot1" });
  });

  it("is a no-op when ctx.removeAutomation is absent", async () => {
    const ctx = {} as AutomationContext;
    await expect(removeAutomationHandler(makeAction("bot1"), ctx, emptyState())).resolves.not.toThrow();
  });

  it("workflow: existing automation row removed from state.automations after action executes", async () => {
    const { AutomationWorkflow } = await import("../../../src/workflow.js");
    const { sendActionsToAutomation } = await import("../../../src/dispatch.js");
    const { emptyState: es, replaceAutomationRow: rr } = await import("../../../src/state.js");
    const { emptyAccountsState } = await import("../../../src/accounts.js");

    const seeded = rr(es(), makeAutomationRow("bot-to-remove"));
    const wf = new AutomationWorkflow();
    const out = await wf.executeAutomation({
      automation: { id: "auto1", metadata: { name: "t", description: "" }, run: async () => ({}) },
      state: seeded,
      accountsState: emptyAccountsState(),
      reason: "test",
      envelopes: [
        sendActionsToAutomation("auto1", [makeAction("bot-to-remove")]),
      ],
      actionHandlers: { remove_automation: removeAutomationHandler },
    });

    const ids = out.state.automations?.map((a) => a.id) ?? [];
    expect(ids).not.toContain("bot-to-remove");
    expect(out.actionExecutions[0].status).toBe(TaskStatus.Completed);
  });

  it("workflow: removing absent automationId is a no-op (state unchanged)", async () => {
    const { AutomationWorkflow } = await import("../../../src/workflow.js");
    const { sendActionsToAutomation } = await import("../../../src/dispatch.js");
    const { emptyState: es, replaceAutomationRow: rr } = await import("../../../src/state.js");
    const { emptyAccountsState } = await import("../../../src/accounts.js");

    const seeded = rr(es(), makeAutomationRow("other-bot"));
    const wf = new AutomationWorkflow();
    const out = await wf.executeAutomation({
      automation: { id: "auto1", metadata: { name: "t", description: "" }, run: async () => ({}) },
      state: seeded,
      accountsState: emptyAccountsState(),
      reason: "test",
      envelopes: [
        sendActionsToAutomation("auto1", [makeAction("nonexistent")]),
      ],
      actionHandlers: { remove_automation: removeAutomationHandler },
    });

    const ids = out.state.automations?.map((a) => a.id) ?? [];
    expect(ids).toContain("other-bot");
    expect(out.actionExecutions[0].status).toBe(TaskStatus.Completed);
  });
});
