import { describe, it, expect } from "vitest";
import { runAutomation } from "../src/runner.js";
import { TaskStatus } from "@drakkarsoftware/octobot-protocol";
import type { Automation } from "../src/runner.js";

const meta = (name: string) => ({ name, description: "" });

const okAutomation = (id: string): Automation => ({
  id,
  metadata: meta(id),
  run: async () => ({ ok: true }),
});

describe("runAutomation", () => {
  it("flows pending → running → completed on happy path", async () => {
    const exec = await runAutomation(okAutomation("a"), { reason: "test", state: { x: 1 } });
    expect(exec.automationId).toBe("a");
    expect(exec.status).toBe(TaskStatus.Completed);
    expect(exec.result).toEqual({ ok: true });
    expect(exec.input).toEqual({ x: 1 });
    expect(exec.completedAt).toBeGreaterThanOrEqual(exec.startedAt);
    expect(exec.error).toBeUndefined();
  });

  it("captures thrown errors with serialized stack", async () => {
    const failing: Automation = {
      id: "b",
      metadata: meta("b"),
      run: async () => {
        throw new Error("boom");
      },
    };
    const exec = await runAutomation(failing, { reason: "test", state: {} });
    expect(exec.status).toBe(TaskStatus.Failed);
    expect(exec.error?.message).toBe("boom");
    expect(exec.error?.name).toBe("Error");
    expect(exec.error?.stack).toContain("boom");
    expect(exec.result).toBeUndefined();
  });

  it("transitions to cancelled when the signal aborts mid-flight", async () => {
    const ctrl = new AbortController();
    const slow: Automation = {
      id: "c",
      metadata: meta("c"),
      run: async (ctx) => {
        ctrl.abort();
        if (ctx.signal.aborted) throw new Error("aborted");
        return {};
      },
    };
    const exec = await runAutomation(slow, { reason: "test", state: {}, signal: ctrl.signal });
    expect(exec.status).toBe(TaskStatus.Cancelled);
    expect(exec.completedAt).toBeGreaterThanOrEqual(exec.startedAt);
  });

  it("returns cancelled immediately when the signal was already aborted", async () => {
    const ctrl = new AbortController();
    ctrl.abort();
    const exec = await runAutomation(okAutomation("d"), {
      reason: "test",
      state: {},
      signal: ctrl.signal,
    });
    expect(exec.status).toBe(TaskStatus.Cancelled);
  });
});
