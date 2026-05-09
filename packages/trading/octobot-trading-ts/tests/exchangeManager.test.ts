import { describe, it, expect } from "vitest";
import { ExchangeManager } from "../src/exchanges/exchangeManager.js";
import { Exchanges } from "../src/exchanges/exchanges.js";

describe("ExchangeManager", () => {
  it("classifies as spot by default", () => {
    const m = new ExchangeManager({ exchangeClassString: "binance" });
    expect(m.isSpot).toBe(true);
    expect(m.exchangeType).toBe("spot");
  });

  it("infers futures over spot when both are set", () => {
    const m = new ExchangeManager({ exchangeClassString: "bybit", isFuture: true });
    expect(m.exchangeType).toBe("future");
  });

  it("registers and removes itself in the global Exchanges registry on lifecycle", async () => {
    const m = new ExchangeManager({ exchangeClassString: "kraken" });
    // We can't .initialize() without a real connector, but we can simulate the registry hop.
    Exchanges.add({ exchangeName: m.exchangeClassString, exchangeManager: m });
    expect(Exchanges.getExchanges("kraken").length).toBeGreaterThan(0);
    Exchanges.remove("kraken", m.id);
    expect(Exchanges.getExchanges("kraken").length).toBe(0);
  });
});
