import { describe, it, expect } from "vitest";
import { ExchangeBuilder, createExchangeBuilderInstance } from "../src/exchangeBuilder.js";
import { ExchangeManager } from "../src/exchangeManager.js";
import { DefaultRestExchange } from "../src/implementations/defaultRestExchange.js";

describe("ExchangeBuilder", () => {
  it("returns an ExchangeManager wrapping a default REST exchange", () => {
    const manager = new ExchangeBuilder("kraken").asSpot().setSandboxed(false).build();
    expect(manager).toBeInstanceOf(ExchangeManager);
    expect(manager.exchange).toBeInstanceOf(DefaultRestExchange);
    expect(manager.isSpot).toBe(true);
    expect(manager.exchangeWebSocket).toBeNull();
  });

  it("builds a futures-flavored manager when asFuture()", () => {
    const manager = createExchangeBuilderInstance("bybit").asFuture().build();
    expect(manager.isFuture).toBe(true);
    expect(manager.isSpot).toBe(false);
  });

  it("wires WebSocket exchange when enableWebSocket()", () => {
    const manager = new ExchangeBuilder("kraken").asSpot().enableWebSocket(true).build();
    expect(manager.exchangeWebSocket).not.toBeNull();
  });

  it("propagates credentials onto the connector", () => {
    const manager = new ExchangeBuilder("kraken")
      .asSpot()
      .setCredentials({ apiKey: "k", secret: "s" })
      .build();
    expect(manager.credentials.apiKey).toBe("k");
    expect(manager.credentials.hasCredentials()).toBe(true);
  });
});
