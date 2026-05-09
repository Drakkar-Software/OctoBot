// Slimmed port of config/exchange_config_data.py — the Python file exposes
// `ExchangeConfig` which the production code uses to track traded pairs,
// timeframes, currencies-by-symbol, and per-symbol settings. The browser
// wrapper supports the same shape but doesn't subscribe to the channel-driven
// updates.

export interface PerSymbolConfig {
  enabled?: boolean;
  [key: string]: unknown;
}

export class ExchangeConfig {
  tradedSymbolPairs: Set<string> = new Set();
  tradedTimeFrames: Set<string> = new Set();
  watchedSymbols: Set<string> = new Set();
  forcedSpecificPairsByExchange: Map<string, string[]> = new Map();
  perSymbolConfig: Map<string, PerSymbolConfig> = new Map();

  initFromConfig(config: Record<string, unknown>): void {
    const pairs = (config["traded_pairs"] as string[]) ?? [];
    for (const p of pairs) this.tradedSymbolPairs.add(p);
    const tfs = (config["traded_timeframes"] as string[]) ?? [];
    for (const t of tfs) this.tradedTimeFrames.add(t);
  }
}
