import { describe, it, expect } from "vitest";
import {
  emptyState,
  appendExecution,
  latestForAutomation,
  latestOverall,
  findAutomationState,
} from "../src/state.js";
import { newExecution, markSuccess } from "../src/execution.js";

describe("state helpers", () => {
  it("emptyState returns a versioned empty AutomationsState", () => {
    const s = emptyState();
    expect(s.version).toBe("1.0.0");
    expect(s.automations).toEqual([]);
  });

  it("appendExecution creates an AutomationState row when missing", () => {
    let s = emptyState();
    const e = markSuccess(newExecution({ automationId: "a", reason: "test" }), { v: 1 });
    s = appendExecution(s, e);
    expect(s.automations?.length).toBe(1);
    expect(s.automations?.[0].id).toBe("a");
    expect(s.automations?.[0].lastExecution).toEqual(e);
    expect(s.automations?.[0].executions).toEqual([e]);
  });

  it("appendExecution appends to history when the row already exists", () => {
    let s = emptyState();
    const e1 = markSuccess(newExecution({ automationId: "a", reason: "first" }), {});
    const e2 = markSuccess(newExecution({ automationId: "a", reason: "second" }), {});
    s = appendExecution(s, e1);
    s = appendExecution(s, e2);
    expect(s.automations?.[0].executions?.length).toBe(2);
    expect(s.automations?.[0].lastExecution).toEqual(e2);
  });

  it("latestForAutomation returns lastExecution or null", () => {
    let s = emptyState();
    expect(latestForAutomation(s, "a")).toBeNull();
    const e = markSuccess(newExecution({ automationId: "a", reason: "" }), {});
    s = appendExecution(s, e);
    expect(latestForAutomation(s, "a")).toEqual(e);
    expect(latestForAutomation(s, "missing")).toBeNull();
  });

  it("latestOverall returns the most recent execution across automations", async () => {
    let s = emptyState();
    const e1 = markSuccess(newExecution({ automationId: "a", reason: "" }), {});
    await new Promise((r) => setTimeout(r, 5));
    const e2 = markSuccess(newExecution({ automationId: "b", reason: "" }), {});
    s = appendExecution(s, e1);
    s = appendExecution(s, e2);
    expect(latestOverall(s)?.automationId).toBe("b");
  });

  it("does not mutate the input state", () => {
    const s1 = emptyState();
    const before = JSON.stringify(s1);
    const e = markSuccess(newExecution({ automationId: "a", reason: "" }), {});
    appendExecution(s1, e);
    expect(JSON.stringify(s1)).toBe(before);
  });

  it("findAutomationState returns null for unknown id", () => {
    const s = emptyState();
    expect(findAutomationState(s, "missing")).toBeNull();
  });
});
