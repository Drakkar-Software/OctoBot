// Slimmed port of abstract_websocket_exchange.py. The Python source pushes
// every received feed onto an `async_channel` named queue; in the browser
// port, downstream code subscribes via `manager.events.on('ticker', cb)` etc.
// The class is responsible for translating exchange-specific feed names to
// the shared OctoBot WebsocketFeeds enum and tracking which (channel, pair,
// timeframe) tuples are active.

import { Logger, getLogger, EventBus } from "@drakkarsoftware/octobot-commons";
import type { ExchangeManager } from "./exchangeManager.js";
import { AbstractExchange } from "./abstractExchange.js";
import { WebsocketFeeds } from "./enums.js";

export interface WebsocketInitOptions {
  currencies?: string[];
  pairs?: string[];
  timeFrames?: string[];
  channels?: WebsocketFeeds[];
}

export abstract class AbstractWebsocketExchange {
  static readonly REQUIRED_ACTIVATED_TENTACLES: string[] = [];
  static readonly EXCHANGE_FEEDS: Record<string, string> = {};
  static readonly INIT_REQUIRING_EXCHANGE_FEEDS: Set<WebsocketFeeds> = new Set();
  static readonly IGNORED_FEED_PAIRS: Record<string, string[]> = {};
  static readonly SUPPORTS_LIVE_PAIR_ADDITION = false;
  static readonly TIME_FRAME_RELATED_FEEDS: WebsocketFeeds[] = [
    WebsocketFeeds.CANDLE,
    WebsocketFeeds.KLINE,
  ];

  config: Record<string, unknown>;
  exchangeManager: ExchangeManager;
  exchange: AbstractExchange | null;
  exchangeId: string;
  events: EventBus;

  currencies: string[] = [];
  pairs: string[] = [];
  timeFrames: string[] = [];
  channels: WebsocketFeeds[] = [];
  books: Record<string, Record<string, unknown>> = {};

  client: unknown = null;
  protected logger: Logger;

  constructor(config: Record<string, unknown>, exchangeManager: ExchangeManager) {
    this.config = config;
    this.exchangeManager = exchangeManager;
    this.exchange = exchangeManager.exchange;
    this.exchangeId = exchangeManager.id;
    this.events = exchangeManager.events;
    this.logger = getLogger(`WebSocket - ${this.constructor.name}`);
  }

  // Subclasses may override to publish their own configured pairs/feeds.
  initializeWithFeeds(opts: WebsocketInitOptions = {}): void {
    this.pairs = (opts.pairs ?? []).map((p) => this.getExchangePair(p));
    this.channels = Array.from(new Set((opts.channels ?? []).map((c) => this.feedToExchange(c) as WebsocketFeeds)));
    this.timeFrames = (opts.timeFrames ?? []).filter((tf) => this.isTimeFrameSupported(tf));
    this.currencies = opts.currencies ?? [];
  }

  abstract initialize(): Promise<void>;
  abstract stop(): Promise<void>;

  isTimeFrameRelatedFeed(feed: WebsocketFeeds): boolean {
    return AbstractWebsocketExchange.TIME_FRAME_RELATED_FEEDS.includes(feed);
  }

  abstract isTimeFrameSupported(timeFrame: string): boolean;

  /** Translate an OctoBot symbol "BTC/USDT" to the exchange-native format. */
  getExchangePair(pair: string): string {
    return pair;
  }

  /** Translate WebsocketFeeds → exchange-native feed name. Subclasses override. */
  feedToExchange(feed: WebsocketFeeds): string {
    const ctor = this.constructor as typeof AbstractWebsocketExchange;
    return ctor.EXCHANGE_FEEDS[feed] ?? feed;
  }

  /** Push a feed message onto the EventBus. */
  protected emit(channel: WebsocketFeeds | string, payload: unknown): void {
    this.events.emit(channel, payload);
  }
}
