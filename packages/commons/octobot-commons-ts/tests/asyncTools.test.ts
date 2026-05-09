import { describe, it, expect } from "vitest";
import { Deferred, AsyncEvent, sleep } from "../src/asyncTools.js";

describe("Deferred", () => {
  it("resolves once and stays settled", async () => {
    const d = new Deferred<number>();
    d.resolve(42);
    d.resolve(99);
    expect(d.settled).toBe(true);
    expect(await d.promise).toBe(42);
  });

  it("rejects with the given reason", async () => {
    const d = new Deferred<number>();
    d.reject(new Error("nope"));
    await expect(d.promise).rejects.toThrow("nope");
  });
});

describe("AsyncEvent", () => {
  it("waits until set", async () => {
    const ev = new AsyncEvent();
    let resolved = false;
    const w = ev.wait().then(() => { resolved = true; });
    expect(resolved).toBe(false);
    ev.set();
    await w;
    expect(resolved).toBe(true);
    expect(ev.isSet()).toBe(true);
  });

  it("clears and re-arms", async () => {
    const ev = new AsyncEvent();
    ev.set();
    expect(ev.isSet()).toBe(true);
    ev.clear();
    expect(ev.isSet()).toBe(false);
    await sleep(1);
  });
});
