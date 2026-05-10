import Decimal from "decimal.js";
import type { AbstractExchange } from "@drakkarsoftware/octobot-trading-exchanges";

const OHLCV_TIMESTAMP = 0;
const OHLCV_OPEN = 1;
const OHLCV_HIGH = 2;
const OHLCV_LOW = 3;
const OHLCV_CLOSE = 4;
const OHLCV_VOLUME = 5;

function decimalAt(kline: number[] | null | undefined, index: number): Decimal {
  return new Decimal(kline?.[index] ?? 0);
}

function decimalField(ticker: Record<string, unknown> | null | undefined, field: string): Decimal {
  return new Decimal((ticker?.[field] as number | string | undefined) ?? 0);
}

function obLevel(book: Record<string, unknown> | null | undefined, side: "bids" | "asks", idx: number): Decimal {
  const levels = book?.[side] as number[][] | undefined;
  return new Decimal(levels?.[0]?.[idx] ?? 0);
}

export interface MarketDataKeywords {
  close(symbol: string, timeFrame: string): Promise<Decimal>;
  open(symbol: string, timeFrame: string): Promise<Decimal>;
  high(symbol: string, timeFrame: string): Promise<Decimal>;
  low(symbol: string, timeFrame: string): Promise<Decimal>;
  volume(symbol: string, timeFrame: string): Promise<Decimal>;
  time(symbol: string, timeFrame: string): Promise<number>;
  ticker_last(symbol: string): Promise<Decimal>;
  ticker_close(symbol: string): Promise<Decimal>;
  ticker_open(symbol: string): Promise<Decimal>;
  ticker_high(symbol: string): Promise<Decimal>;
  ticker_low(symbol: string): Promise<Decimal>;
  ticker_volume(symbol: string): Promise<Decimal>;
  bid(symbol: string): Promise<Decimal>;
  ask(symbol: string): Promise<Decimal>;
  bid_volume(symbol: string): Promise<Decimal>;
  ask_volume(symbol: string): Promise<Decimal>;
}

export function createMarketDataKeywords(exchange: AbstractExchange): MarketDataKeywords {
  return {
    async close(symbol, timeFrame) {
      return decimalAt(await exchange.getKlinePrice(symbol, timeFrame), OHLCV_CLOSE);
    },
    async open(symbol, timeFrame) {
      return decimalAt(await exchange.getKlinePrice(symbol, timeFrame), OHLCV_OPEN);
    },
    async high(symbol, timeFrame) {
      return decimalAt(await exchange.getKlinePrice(symbol, timeFrame), OHLCV_HIGH);
    },
    async low(symbol, timeFrame) {
      return decimalAt(await exchange.getKlinePrice(symbol, timeFrame), OHLCV_LOW);
    },
    async volume(symbol, timeFrame) {
      return decimalAt(await exchange.getKlinePrice(symbol, timeFrame), OHLCV_VOLUME);
    },
    async time(symbol, timeFrame) {
      return (await exchange.getKlinePrice(symbol, timeFrame))?.[OHLCV_TIMESTAMP] ?? 0;
    },
    async ticker_last(symbol) {
      return decimalField(await exchange.getPriceTicker(symbol), "last");
    },
    async ticker_close(symbol) {
      return decimalField(await exchange.getPriceTicker(symbol), "close");
    },
    async ticker_open(symbol) {
      return decimalField(await exchange.getPriceTicker(symbol), "open");
    },
    async ticker_high(symbol) {
      return decimalField(await exchange.getPriceTicker(symbol), "high");
    },
    async ticker_low(symbol) {
      return decimalField(await exchange.getPriceTicker(symbol), "low");
    },
    async ticker_volume(symbol) {
      return decimalField(await exchange.getPriceTicker(symbol), "baseVolume");
    },
    async bid(symbol) {
      return obLevel(await exchange.getOrderBook(symbol, 1), "bids", 0);
    },
    async ask(symbol) {
      return obLevel(await exchange.getOrderBook(symbol, 1), "asks", 0);
    },
    async bid_volume(symbol) {
      return obLevel(await exchange.getOrderBook(symbol, 1), "bids", 1);
    },
    async ask_volume(symbol) {
      return obLevel(await exchange.getOrderBook(symbol, 1), "asks", 1);
    },
  };
}
