// Mirror of connectors/ccxt/ccxt_clients_cache.py — keeps a singleton CCXTExchange
// per (exchange, sandboxed) pair so we don't repeatedly call loadMarkets().
// The Python file caches via Markets file storage; in the browser we just keep
// markets in-memory per client.

import type { Exchange as CCXTExchange } from "ccxt";

interface CacheEntry {
  client: CCXTExchange;
  marketsLoadedAt: number;
}

const cache = new Map<string, CacheEntry>();

function key(exchangeName: string, sandboxed: boolean): string {
  return `${exchangeName}:${sandboxed ? "sandbox" : "live"}`;
}

export function getCachedClient(exchangeName: string, sandboxed: boolean): CCXTExchange | null {
  return cache.get(key(exchangeName, sandboxed))?.client ?? null;
}

export function cacheClient(exchangeName: string, sandboxed: boolean, client: CCXTExchange): void {
  cache.set(key(exchangeName, sandboxed), { client, marketsLoadedAt: Date.now() });
}

export function invalidate(exchangeName: string, sandboxed: boolean): void {
  cache.delete(key(exchangeName, sandboxed));
}

export function clearAll(): void {
  cache.clear();
}
