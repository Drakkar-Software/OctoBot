// Slimmed port of util/websockets_util.py. Tentacle-discovery functions are
// replaced with the static registry below — callers register their custom
// WebSocketExchange class via `registerWebsocketClass` and the factory looks
// it up by exchange name.

import type { ExchangeProxyConfig } from "../config/exchangeProxyConfig.js";

type WebsocketCtor = new (...args: unknown[]) => unknown;
const websocketRegistry: Map<string, WebsocketCtor> = new Map();

export function registerWebsocketClass(exchangeName: string, klass: WebsocketCtor): void {
  websocketRegistry.set(exchangeName, klass);
}

export function getWebsocketClass(exchangeName: string): WebsocketCtor | null {
  return websocketRegistry.get(exchangeName) ?? null;
}

export function searchWebsocketClass(exchangeName: string): WebsocketCtor | null {
  return getWebsocketClass(exchangeName);
}

export function forceDisableWebSocket(config: Record<string, unknown>, exchangeName: string): boolean {
  const exchanges = config["exchanges"] as Record<string, Record<string, unknown>> | undefined;
  const cfg = exchanges?.[exchangeName];
  return !!cfg && cfg["web-socket"] === false;
}

export function checkWebSocketConfig(config: Record<string, unknown>, exchangeName: string): boolean {
  return !forceDisableWebSocket(config, exchangeName);
}

export function isProxyConfigCompatibleWithWebsocketConnector(
  websocketConnectorClass: { REQUIRES_PROXY_IF_REST_PROXY_ENABLED?: boolean },
  proxyConfig: ExchangeProxyConfig,
): boolean {
  if (websocketConnectorClass.REQUIRES_PROXY_IF_REST_PROXY_ENABLED && proxyConfig.hasRestProxy() && !proxyConfig.hasWebsocketProxy()) {
    return false;
  }
  return true;
}

export function supportsWebsocket(exchangeName: string): boolean {
  return websocketRegistry.has(exchangeName);
}
