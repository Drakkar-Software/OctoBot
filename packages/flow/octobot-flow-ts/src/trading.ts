import Decimal from "decimal.js";
import type { AbstractExchange } from "@drakkarsoftware/octobot-trading-exchanges";
import { TraderOrderType } from "@drakkarsoftware/octobot-trading-exchanges";

function toDec(x: number | string | Decimal): Decimal {
  return x instanceof Decimal ? x : new Decimal(x);
}

export interface TradingKeywords {
  market(side: "buy" | "sell", symbol: string, qty: number | string | Decimal): Promise<unknown>;
  limit(side: "buy" | "sell", symbol: string, qty: number | string | Decimal, price: number | string | Decimal): Promise<unknown>;
  cancel_order(symbol: string): Promise<string[]>;
  fetch_order(id: string, symbol: string): Promise<unknown>;
  fetch_trades(symbol?: string, limit?: number): Promise<Record<string, unknown>[]>;
  total(asset: string): Promise<Decimal>;
  available(asset: string): Promise<Decimal>;
}

export function createTradingKeywords(exchange: AbstractExchange): TradingKeywords {
  return {
    async market(side, symbol, qty) {
      const orderType = side === "buy" ? TraderOrderType.BUY_MARKET : TraderOrderType.SELL_MARKET;
      return exchange.createOrder(orderType, symbol, toDec(qty));
    },

    async limit(side, symbol, qty, price) {
      const orderType = side === "buy" ? TraderOrderType.BUY_LIMIT : TraderOrderType.SELL_LIMIT;
      return exchange.createOrder(orderType, symbol, toDec(qty), toDec(price));
    },

    async cancel_order(symbol) {
      const orders = await exchange.getOpenOrders(symbol);
      const ids = orders
        .map((o) => String(o["id"] ?? o["exchange_id"] ?? ""))
        .filter(Boolean);
      await Promise.all(ids.map((id) => exchange.cancelOrder(id, symbol, TraderOrderType.BUY_MARKET)));
      return ids;
    },

    async fetch_order(id, symbol) {
      return exchange.getOrder(id, symbol);
    },

    async fetch_trades(symbol, limit) {
      return exchange.getMyRecentTrades(symbol, undefined, limit);
    },

    async total(asset) {
      const balance = await exchange.getBalance();
      const entry = balance?.[asset] as { total?: Decimal } | undefined;
      return entry?.total ?? new Decimal(0);
    },

    async available(asset) {
      const balance = await exchange.getBalance();
      const entry = balance?.[asset] as { available?: Decimal } | undefined;
      return entry?.available ?? new Decimal(0);
    },
  };
}
