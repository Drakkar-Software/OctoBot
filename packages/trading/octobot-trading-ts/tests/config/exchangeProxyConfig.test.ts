import { describe, it, expect } from "vitest";
import { ExchangeProxyConfig } from "../../src/exchanges/config/exchangeProxyConfig.js";

describe("ExchangeProxyConfig", () => {
  it("reports presence of REST/WebSocket proxies", () => {
    const empty = new ExchangeProxyConfig();
    expect(empty.hasRestProxy()).toBe(false);
    expect(empty.hasWebsocketProxy()).toBe(false);

    const rest = new ExchangeProxyConfig({ httpProxy: "http://p:8080" });
    expect(rest.hasRestProxy()).toBe(true);
    expect(rest.hasWebsocketProxy()).toBe(false);

    const ws = new ExchangeProxyConfig({ wssProxy: "wss://p:8081" });
    expect(ws.hasRestProxy()).toBe(false);
    expect(ws.hasWebsocketProxy()).toBe(true);
  });
});
