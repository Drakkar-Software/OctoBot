// Mirror of exchanges.py — registry of running ExchangeManagers, simplified.
// In Python this is a singleton holding ExchangeConfiguration instances; here
// we expose the same shape but without async_channel side effects.

import type { ExchangeManager } from "./exchangeManager.js";

export interface ExchangeConfiguration {
  exchangeName: string;
  exchangeManager: ExchangeManager;
}

class ExchangesRegistry {
  private byName: Map<string, ExchangeConfiguration[]> = new Map();

  add(exchangeConfig: ExchangeConfiguration): void {
    const existing = this.byName.get(exchangeConfig.exchangeName) ?? [];
    existing.push(exchangeConfig);
    this.byName.set(exchangeConfig.exchangeName, existing);
  }

  remove(exchangeName: string, exchangeManagerId: string): void {
    const list = this.byName.get(exchangeName);
    if (!list) return;
    const filtered = list.filter((cfg) => cfg.exchangeManager.id !== exchangeManagerId);
    if (filtered.length === 0) this.byName.delete(exchangeName);
    else this.byName.set(exchangeName, filtered);
  }

  getExchanges(exchangeName: string): ExchangeConfiguration[] {
    return this.byName.get(exchangeName) ?? [];
  }

  getExchangesNames(): string[] {
    return Array.from(this.byName.keys());
  }

  clear(): void {
    this.byName.clear();
  }
}

export const Exchanges = new ExchangesRegistry();
