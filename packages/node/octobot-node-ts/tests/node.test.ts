import { describe, it, expect, vi } from "vitest";
import { createOctobotNode, emptyState } from "../src/node.js";
import { TaskStatus } from "@drakkarsoftware/octobot-protocol";
import type { AutomationsState, Execution } from "@drakkarsoftware/octobot-protocol";

describe("OctobotNode.run", () => {
  it("fires every registered automation by default and folds executions into nextState", async () => {
    const node = createOctobotNode();
    const a = vi.fn(async () => ({ from: "a" }));
    const b = vi.fn(async () => ({ from: "b" }));
    node.registerAutomation({ id: "a", name: "a", run: a });
    node.registerAutomation({ id: "b", name: "b", run: b });

    const { executions, nextState } = await node.run({
      state: emptyState(),
      reason: "test tick",
    });

    expect(a).toHaveBeenCalledTimes(1);
    expect(b).toHaveBeenCalledTimes(1);
    expect(executions.map((e) => e.automationId)).toEqual(["a", "b"]);
    expect(executions.every((e) => e.status === TaskStatus.Completed)).toBe(true);
    expect(executions.every((e) => e.reason === "test tick")).toBe(true);
    expect(nextState.automations?.length).toBe(2);
  });

  it("automationIds bypasses shouldRun and runs only the named subset", async () => {
    const node = createOctobotNode();
    const a = vi.fn(async () => ({}));
    const b = vi.fn(async () => ({}));
    node.registerAutomation({ id: "a", name: "a", shouldRun: () => false, run: a });
    node.registerAutomation({ id: "b", name: "b", run: b });

    const { executions } = await node.run({
      state: emptyState(),
      reason: "targeted",
      automationIds: ["a"],
    });

    expect(a).toHaveBeenCalledTimes(1);   // bypassed shouldRun
    expect(b).not.toHaveBeenCalled();
    expect(executions.map((e) => e.automationId)).toEqual(["a"]);
  });

  it("shouldRun returning false produces no execution row", async () => {
    const node = createOctobotNode();
    node.registerAutomation({
      id: "a",
      name: "a",
      shouldRun: () => false,
      run: async () => ({}),
    });
    node.registerAutomation({
      id: "b",
      name: "b",
      run: async () => ({}),
    });

    const { executions, nextState } = await node.run({
      state: emptyState(),
      reason: "test",
    });
    expect(executions.map((e) => e.automationId)).toEqual(["b"]);
    expect(nextState.automations?.map((a) => a.id)).toEqual(["b"]);
  });

  it("a failing automation does not block the others", async () => {
    const node = createOctobotNode();
    node.registerAutomation({
      id: "bad",
      name: "bad",
      run: async () => { throw new Error("boom"); },
    });
    node.registerAutomation({
      id: "good",
      name: "good",
      run: async () => ({ ok: true }),
    });

    const { executions } = await node.run({
      state: emptyState(),
      reason: "test",
    });
    expect(executions.map((e) => e.status)).toEqual([TaskStatus.Failed, TaskStatus.Completed]);
    expect(executions[0].error?.message).toBe("boom");
  });

  it("each automation sees the latest nextState (so subsequent ones can read prior executions)", async () => {
    const node = createOctobotNode();
    let observed: Execution | null | undefined;
    node.registerAutomation({
      id: "first",
      name: "first",
      run: async () => ({ value: 1 }),
    });
    node.registerAutomation({
      id: "second",
      name: "second",
      run: async (_ctx, state: AutomationsState) => {
        observed = node.latestForAutomation(state, "first");
        return {};
      },
    });

    await node.run({ state: emptyState(), reason: "chained" });
    expect(observed).toBeTruthy();
    expect(observed?.automationId).toBe("first");
    expect(observed?.result).toEqual({ value: 1 });
  });

  it("aborting the signal stops not-yet-started automations", async () => {
    const node = createOctobotNode();
    const ctrl = new AbortController();
    let bRan = false;
    node.registerAutomation({
      id: "a",
      name: "a",
      run: async () => { ctrl.abort(); return {}; },
    });
    node.registerAutomation({
      id: "b",
      name: "b",
      run: async () => { bRan = true; return {}; },
    });

    const { executions } = await node.run({
      state: emptyState(),
      reason: "test",
      signal: ctrl.signal,
    });
    expect(bRan).toBe(false);
    // a aborted itself mid-flight → cancelled; b never ran → no record
    expect(executions.map((e) => e.automationId)).toEqual(["a"]);
    expect(executions[0].status).toBe(TaskStatus.Cancelled);
  });

  it("listAutomations returns automations in registration order", () => {
    const node = createOctobotNode();
    node.registerAutomation({ id: "z", name: "z", run: async () => ({}) });
    node.registerAutomation({ id: "a", name: "a", run: async () => ({}) });
    expect(node.listAutomations().map((x) => x.id)).toEqual(["z", "a"]);
  });
});
