import { describe, it, expect } from "vitest";
import { AutomationRegistry } from "../src/automation.js";
import { DuplicateAutomationError, AutomationNotFoundError } from "../src/errors.js";

const stub = (id: string) => ({
  id,
  name: id,
  run: async () => ({}),
});

describe("AutomationRegistry", () => {
  it("registers and lists in insertion order", () => {
    const r = new AutomationRegistry();
    r.register(stub("a"));
    r.register(stub("b"));
    r.register(stub("c"));
    expect(r.list().map((x) => x.id)).toEqual(["a", "b", "c"]);
  });

  it("rejects duplicate IDs", () => {
    const r = new AutomationRegistry();
    r.register(stub("x"));
    expect(() => r.register(stub("x"))).toThrow(DuplicateAutomationError);
  });

  it("get throws AutomationNotFoundError for unknown ids", () => {
    const r = new AutomationRegistry();
    expect(() => r.get("missing")).toThrow(AutomationNotFoundError);
    expect(r.has("missing")).toBe(false);
  });

  it("unregister removes the automation and updates list order", () => {
    const r = new AutomationRegistry();
    r.register(stub("a"));
    r.register(stub("b"));
    expect(r.unregister("a")).toBe(true);
    expect(r.list().map((x) => x.id)).toEqual(["b"]);
    expect(r.unregister("a")).toBe(false);
  });
});
