// Slimmed port of connectors/ccxt/ccxt_client_util.py — only the helpers that
// browser callers and the connector need.

// Use `ccxt` package — it's an isomorphic ESM bundle (Node + browser).
import ccxt, { Exchange as CCXTExchange } from "ccxt";

export function getCcxtExchangeClass(name: string): new (config: Record<string, unknown>) => CCXTExchange {
  const klass = (ccxt as unknown as Record<string, unknown>)[name];
  if (typeof klass !== "function") {
    throw new Error(`CCXT exchange class not found: ${name}`);
  }
  return klass as new (config: Record<string, unknown>) => CCXTExchange;
}

export function setSandboxMode(client: CCXTExchange, sandboxed: boolean): void {
  if (typeof client.setSandboxMode === "function") {
    client.setSandboxMode(sandboxed);
  } else if (sandboxed && client.urls && (client.urls as Record<string, unknown>)["test"]) {
    client.urls["api"] = (client.urls as Record<string, unknown>)["test"] as Record<string, string>;
  }
}

export function getCcxtClientLoginOptions(_exchangeManager: unknown): Record<string, unknown> {
  // The Python equivalent reads encrypted credentials and tentacle-level options.
  // In the browser port, callers pass auth via ExchangeCredentialsData on the
  // builder; this hook exists for forward compatibility / overrides.
  return {};
}
