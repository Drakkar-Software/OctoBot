// Mirror of types/websocket_exchange.py. WebSocketExchange acts as a thin
// orchestrator on top of a CCXTWebsocketConnector, exposing watch* style
// methods that emit normalized payloads on the manager's EventBus.

import type { ExchangeManager } from "../exchangeManager.js";
import { AbstractWebsocketExchange } from "../abstractWebsocketExchange.js";
import { CCXTWebsocketConnector } from "../connectors/ccxt/ccxtWebsocketConnector.js";
import { WebsocketFeeds } from "../enums.js";

export class WebSocketExchange extends AbstractWebsocketExchange {
  protected connector: CCXTWebsocketConnector;
  protected runningLoops: Map<string, AbortController> = new Map();

  constructor(
    config: Record<string, unknown>,
    exchangeManager: ExchangeManager,
    connector: CCXTWebsocketConnector,
  ) {
    super(config, exchangeManager);
    this.connector = connector;
  }

  async initialize(): Promise<void> {
    await this.connector.initialize();
  }

  async stop(): Promise<void> {
    for (const ctrl of this.runningLoops.values()) ctrl.abort();
    this.runningLoops.clear();
    await this.connector.stop();
  }

  isTimeFrameSupported(timeFrame: string): boolean {
    const tfs = this.connector.getClient().timeframes ?? {};
    return timeFrame in tfs;
  }

  // ---- watch helpers — start a streaming loop for one (feed, pair) tuple ----

  watchTicker(symbol: string): void {
    this.startWatchLoop(`${WebsocketFeeds.TICKER}:${symbol}`, async (signal) => {
      while (!signal.aborted) {
        const t = await this.connector.watchTicker(symbol);
        this.emit(WebsocketFeeds.TICKER, t);
      }
    });
  }

  watchOHLCV(symbol: string, timeFrame: string): void {
    this.startWatchLoop(`${WebsocketFeeds.CANDLE}:${symbol}:${timeFrame}`, async (signal) => {
      while (!signal.aborted) {
        const c = await this.connector.watchOHLCV(symbol, timeFrame);
        this.emit(WebsocketFeeds.CANDLE, { symbol, timeFrame, candles: c });
      }
    });
  }

  watchTrades(symbol: string): void {
    this.startWatchLoop(`${WebsocketFeeds.TRADES}:${symbol}`, async (signal) => {
      while (!signal.aborted) {
        const trades = await this.connector.watchTrades(symbol);
        this.emit(WebsocketFeeds.TRADES, { symbol, trades });
      }
    });
  }

  watchOrderBook(symbol: string, limit?: number): void {
    this.startWatchLoop(`${WebsocketFeeds.L2_BOOK}:${symbol}`, async (signal) => {
      while (!signal.aborted) {
        const ob = await this.connector.watchOrderBook(symbol, limit);
        this.emit(WebsocketFeeds.L2_BOOK, { symbol, orderBook: ob });
      }
    });
  }

  watchOrders(symbol?: string): void {
    this.startWatchLoop(`${WebsocketFeeds.ORDERS}:${symbol ?? "*"}`, async (signal) => {
      while (!signal.aborted) {
        const orders = await this.connector.watchOrders(symbol);
        this.emit(WebsocketFeeds.ORDERS, { symbol, orders });
      }
    });
  }

  watchBalance(): void {
    this.startWatchLoop(`${WebsocketFeeds.PORTFOLIO}`, async (signal) => {
      while (!signal.aborted) {
        const balance = await this.connector.watchBalance();
        this.emit(WebsocketFeeds.PORTFOLIO, balance);
      }
    });
  }

  protected startWatchLoop(key: string, run: (signal: AbortSignal) => Promise<void>): void {
    if (this.runningLoops.has(key)) return;
    const ctrl = new AbortController();
    this.runningLoops.set(key, ctrl);
    void run(ctrl.signal).catch((err) => {
      if (!ctrl.signal.aborted) this.logger.exception(err, `watch loop "${key}" failed`);
    });
  }

  stopWatch(key: string): void {
    const ctrl = this.runningLoops.get(key);
    if (ctrl) {
      ctrl.abort();
      this.runningLoops.delete(key);
    }
  }
}
