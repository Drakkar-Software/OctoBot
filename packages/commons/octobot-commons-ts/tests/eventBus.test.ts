import { describe, it, expect, vi } from "vitest";
import { EventBus } from "../src/eventBus.js";

describe("EventBus", () => {
  it("calls subscribers and returns an unsubscribe function", () => {
    const bus = new EventBus();
    const cb = vi.fn();
    const off = bus.on<string>("ticker", cb);
    bus.emit("ticker", "x");
    bus.emit("ticker", "y");
    expect(cb).toHaveBeenCalledTimes(2);
    off();
    bus.emit("ticker", "z");
    expect(cb).toHaveBeenCalledTimes(2);
  });

  it("isolates one listener's throw from others", () => {
    const bus = new EventBus();
    const bad = vi.fn(() => { throw new Error("boom"); });
    const good = vi.fn();
    bus.on("t", bad);
    bus.on("t", good);
    expect(() => bus.emit("t", 1)).not.toThrow();
    expect(good).toHaveBeenCalledTimes(1);
  });
});
