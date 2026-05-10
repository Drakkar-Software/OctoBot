import { describe, it, expect, vi } from "vitest";
import { actionToAutomation, applyExecutionToAction } from "../src/actions.js";
import { TaskStatus } from "@drakkarsoftware/octobot-protocol";
import type { Action, Execution } from "@drakkarsoftware/octobot-protocol";
import { newExecution, markSuccess, markFailed, markCancelled } from "../src/execution.js";
import { emptyState } from "../src/state.js";

const action = (id: string, actionType = "noop"): Action => ({
  id,
  actionType,
  status: TaskStatus.Pending,
});

const baseExec = (automationId: string): Execution =>
  newExecution({ automationId, reason: "test" });

describe("actionToAutomation", () => {
  it("produces an Automation with id and metadata from the Action", () => {
    const a = action("act1", "my-action");
    const handler = vi.fn(async () => ({ ok: true }));
    const auto = actionToAutomation(a, handler);
    expect(auto.id).toBe("act1");
    expect(auto.metadata.name).toBe("my-action");
    expect(auto.metadata.description).toBe("");
  });

  it("adapter run invokes the handler with (action, ctx, state) and returns its result", async () => {
    const a = action("act1", "noop");
    const handler = vi.fn(async (_action: Action, _ctx: any, _state: any) => ({ done: true }));
    const auto = actionToAutomation(a, handler);
    const fakeCtx = { executionId: "e1", reason: "test", signal: new AbortController().signal, logger: { debug: vi.fn(), info: vi.fn(), warning: vi.fn(), error: vi.fn(), exception: vi.fn() } as any };
    const result = await auto.run(fakeCtx, emptyState());
    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler).toHaveBeenCalledWith(a, fakeCtx, emptyState());
    expect(result).toEqual({ done: true });
  });
});

describe("applyExecutionToAction", () => {
  it("Completed — sets status, completedAt (Date), result (JSON string)", () => {
    const a = action("act1");
    const exec = markSuccess(markCancelled(baseExec("act1")), { value: 42 });
    const successExec = markSuccess(newExecution({ automationId: "act1", reason: "t" }), { value: 42 });
    const resolved = applyExecutionToAction(a, successExec);
    expect(resolved.status).toBe(TaskStatus.Completed);
    expect(resolved.completedAt).toBeInstanceOf(Date);
    expect(resolved.result).toBe(JSON.stringify({ value: 42 }));
    expect(resolved.error).toBeUndefined();
  });

  it("Failed — sets status, completedAt, error message; clears result", () => {
    const a = action("act1");
    const failedExec = markFailed(newExecution({ automationId: "act1", reason: "t" }), new Error("boom"));
    const resolved = applyExecutionToAction(a, failedExec);
    expect(resolved.status).toBe(TaskStatus.Failed);
    expect(resolved.completedAt).toBeInstanceOf(Date);
    expect(resolved.error).toBe("boom");
    expect(resolved.result).toBeUndefined();
  });

  it("Cancelled — sets status and completedAt only", () => {
    const a = action("act1");
    const cancelledExec = markCancelled(newExecution({ automationId: "act1", reason: "t" }));
    const resolved = applyExecutionToAction(a, cancelledExec);
    expect(resolved.status).toBe(TaskStatus.Cancelled);
    expect(resolved.completedAt).toBeInstanceOf(Date);
  });

  it("preserves all other Action fields unchanged", () => {
    const a: Action = { id: "x", actionType: "my-type", status: TaskStatus.Pending, dsl: "some-dsl" };
    const exec = markSuccess(newExecution({ automationId: "x", reason: "t" }), {});
    const resolved = applyExecutionToAction(a, exec);
    expect(resolved.id).toBe("x");
    expect(resolved.actionType).toBe("my-type");
    expect(resolved.dsl).toBe("some-dsl");
  });
});
