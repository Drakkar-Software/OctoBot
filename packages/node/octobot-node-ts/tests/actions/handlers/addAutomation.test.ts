import { describe, it, expect, vi } from "vitest";
import { TaskStatus } from "@drakkarsoftware/octobot-protocol";
import type { AddAutomationAction, AutomationState } from "@drakkarsoftware/octobot-protocol";
import { addAutomationHandler } from "../../../src/actions/handlers/index.js";
import { emptyState } from "../../../src/state.js";
import type { AutomationContext } from "../../../src/runner.js";

function makeAutomationRow(id: string): AutomationState {
  return { id, status: TaskStatus.Pending, metadata: { name: id, description: "" } };
}

function makeAction(automation: AutomationState): AddAutomationAction {
  return { id: "a1", actionType: "add_automation", status: TaskStatus.Pending, automation };
}

describe("addAutomationHandler", () => {
  it("calls ctx.replaceAutomation and returns the row", async () => {
    const row = makeAutomationRow("bot1");
    const replaceAutomation = vi.fn();
    const ctx = { replaceAutomation } as unknown as AutomationContext;

    const result = await addAutomationHandler(makeAction(row), ctx, emptyState());

    expect(replaceAutomation).toHaveBeenCalledOnce();
    expect(replaceAutomation).toHaveBeenCalledWith(row);
    expect(result).toBe(row);
  });

  it("is a no-op when ctx.replaceAutomation is absent", async () => {
    const ctx = {} as AutomationContext;
    await expect(addAutomationHandler(makeAction(makeAutomationRow("x")), ctx, emptyState())).resolves.not.toThrow();
  });

  it("workflow: automation row appears in output state.automations after action executes", async () => {
    const { AutomationWorkflow } = await import("../../../src/workflow.js");
    const { sendActionsToAutomation } = await import("../../../src/dispatch.js");
    const { emptyState: es } = await import("../../../src/state.js");
    const { emptyAccountsState } = await import("../../../src/accounts.js");

    const row = makeAutomationRow("new-bot");
    const wf = new AutomationWorkflow();
    const out = await wf.executeAutomation({
      automation: { id: "auto1", metadata: { name: "t", description: "" }, run: async () => ({}) },
      state: es(),
      accountsState: emptyAccountsState(),
      reason: "test",
      envelopes: [
        sendActionsToAutomation("auto1", [makeAction(row)]),
      ],
      actionHandlers: { add_automation: addAutomationHandler },
    });

    const ids = out.state.automations?.map((a) => a.id) ?? [];
    expect(ids).toContain("new-bot");
    expect(out.actionExecutions[0].status).toBe(TaskStatus.Completed);
  });
});
