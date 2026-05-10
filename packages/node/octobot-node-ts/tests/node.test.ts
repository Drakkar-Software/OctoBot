import { describe, it, expect, vi } from "vitest";
import { createOctobotNode, emptyState } from "../src/node.js";
import { AutomationNotFoundError } from "../src/errors.js";
import { TaskStatus } from "@drakkarsoftware/octobot-protocol";
import type { AutomationsState, Execution } from "@drakkarsoftware/octobot-protocol";

const meta = (name: string) => ({ name, description: "" });

describe("OctobotNode.run", () => {
  it("fires every automation and folds executions into nextState", async () => {
    const node = createOctobotNode();
    const a = vi.fn(async () => ({ from: "a" }));
    const b = vi.fn(async () => ({ from: "b" }));

    const { executions, nextState } = await node.run({
      automations: [
        { id: "a", metadata: meta("a"), run: a },
        { id: "b", metadata: meta("b"), run: b },
      ],
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

  it("nextState carries correct automation metadata", async () => {
    const node = createOctobotNode();

    const { nextState } = await node.run({
      automations: [{ id: "a", metadata: { name: "My Auto", description: "desc" }, run: async () => ({}) }],
      state: emptyState(),
      reason: "test",
    });

    expect(nextState.automations?.[0].metadata).toEqual({ name: "My Auto", description: "desc" });
  });

  it("automationIds bypasses shouldRun and runs only the named subset", async () => {
    const node = createOctobotNode();
    const a = vi.fn(async () => ({}));
    const b = vi.fn(async () => ({}));

    const { executions } = await node.run({
      automations: [
        { id: "a", metadata: meta("a"), shouldRun: () => false, run: a },
        { id: "b", metadata: meta("b"), run: b },
      ],
      state: emptyState(),
      reason: "targeted",
      automationIds: ["a"],
    });

    expect(a).toHaveBeenCalledTimes(1);
    expect(b).not.toHaveBeenCalled();
    expect(executions.map((e) => e.automationId)).toEqual(["a"]);
  });

  it("automationIds throws AutomationNotFoundError for unknown id", async () => {
    const node = createOctobotNode();
    await expect(
      node.run({
        automations: [{ id: "a", metadata: meta("a"), run: async () => ({}) }],
        state: emptyState(),
        reason: "test",
        automationIds: ["missing"],
      }),
    ).rejects.toThrow(AutomationNotFoundError);
  });

  it("shouldRun returning false produces no execution row", async () => {
    const node = createOctobotNode();

    const { executions, nextState } = await node.run({
      automations: [
        { id: "a", metadata: meta("a"), shouldRun: () => false, run: async () => ({}) },
        { id: "b", metadata: meta("b"), run: async () => ({}) },
      ],
      state: emptyState(),
      reason: "test",
    });

    expect(executions.map((e) => e.automationId)).toEqual(["b"]);
    expect(nextState.automations?.map((a) => a.id)).toEqual(["b"]);
  });

  it("a failing automation does not block the others", async () => {
    const node = createOctobotNode();

    const { executions } = await node.run({
      automations: [
        { id: "bad", metadata: meta("bad"), run: async () => { throw new Error("boom"); } },
        { id: "good", metadata: meta("good"), run: async () => ({ ok: true }) },
      ],
      state: emptyState(),
      reason: "test",
    });

    expect(executions.map((e) => e.status)).toEqual([TaskStatus.Failed, TaskStatus.Completed]);
    expect(executions[0].error?.message).toBe("boom");
  });

  it("each automation sees the latest nextState (so subsequent ones can read prior executions)", async () => {
    const node = createOctobotNode();
    let observed: Execution | null | undefined;

    await node.run({
      automations: [
        { id: "first", metadata: meta("first"), run: async () => ({ value: 1 }) },
        {
          id: "second",
          metadata: meta("second"),
          run: async (_ctx, state: AutomationsState) => {
            observed = node.latestForAutomation(state, "first");
            return {};
          },
        },
      ],
      state: emptyState(),
      reason: "chained",
    });

    expect(observed).toBeTruthy();
    expect(observed?.automationId).toBe("first");
    expect(observed?.result).toEqual({ value: 1 });
  });

  it("aborting the signal stops not-yet-started automations", async () => {
    const node = createOctobotNode();
    const ctrl = new AbortController();
    let bRan = false;

    const { executions } = await node.run({
      automations: [
        { id: "a", metadata: meta("a"), run: async () => { ctrl.abort(); return {}; } },
        { id: "b", metadata: meta("b"), run: async () => { bRan = true; return {}; } },
      ],
      state: emptyState(),
      reason: "test",
      signal: ctrl.signal,
    });

    expect(bRan).toBe(false);
    expect(executions.map((e) => e.automationId)).toEqual(["a"]);
    expect(executions[0].status).toBe(TaskStatus.Cancelled);
  });
});
