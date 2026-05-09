// Slimmed port of exchange_manager.py — ~400 LOC of orchestration in Python,
// most of which wires async_channel producers/consumers, personal_data
// containers, signal-driven authentication checks, and tentacle setup.
// In the browser-first port we keep the central role (a façade that owns the
// REST exchange, the WS exchange, config, identity flags) and drop everything
// rooted in the channel/tentacle systems.

import { AbstractExchange, ExchangeManagerLike } from "./abstractExchange.js";
import type { AbstractWebsocketExchange } from "./abstractWebsocketExchange.js";
import { ExchangeProxyConfig } from "./config/exchangeProxyConfig.js";
import { ExchangeCredentialsData } from "./config/exchangeCredentialsData.js";
import { Exchanges } from "./exchanges.js";
import { Logger, getLogger } from "./util/logger.js";
import { EventBus } from "./util/eventBus.js";
import { ExchangeTypes } from "./enums.js";

export interface ExchangeManagerOptions {
  exchangeClassString: string;
  config?: Record<string, unknown>;
  isSpot?: boolean;
  isFuture?: boolean;
  isMargin?: boolean;
  isOption?: boolean;
  isSandboxed?: boolean;
  credentials?: ExchangeCredentialsData;
  proxy?: ExchangeProxyConfig;
  tentaclesSetupConfig?: unknown;
  // optional WS-related flag (mirrors ws_disabled / force_disable_web_socket).
  webSocketEnabled?: boolean;
}

let _idCounter = 0;
function nextId(): string {
  _idCounter += 1;
  return `exchange-${Date.now()}-${_idCounter}`;
}

export class ExchangeManager implements ExchangeManagerLike {
  readonly id: string;
  exchangeClassString: string;
  config: Record<string, unknown>;
  isSpot: boolean;
  isFuture: boolean;
  isMargin: boolean;
  isOption: boolean;
  isSandboxed: boolean;
  isInitialized = false;
  isStopped = false;
  webSocketEnabled: boolean;

  credentials: ExchangeCredentialsData;
  proxyConfig: ExchangeProxyConfig | null;
  tentaclesSetupConfig: unknown;

  // wired by ExchangeBuilder.
  exchange: AbstractExchange | null = null;
  exchangeWebSocket: AbstractWebsocketExchange | null = null;

  readonly events: EventBus = new EventBus();
  protected logger: Logger;

  constructor(opts: ExchangeManagerOptions) {
    this.id = nextId();
    this.exchangeClassString = opts.exchangeClassString;
    this.config = opts.config ?? {};
    this.isSpot = opts.isSpot ?? !(opts.isFuture || opts.isMargin || opts.isOption);
    this.isFuture = opts.isFuture ?? false;
    this.isMargin = opts.isMargin ?? false;
    this.isOption = opts.isOption ?? false;
    this.isSandboxed = opts.isSandboxed ?? false;
    this.webSocketEnabled = opts.webSocketEnabled ?? false;
    this.credentials = opts.credentials ?? new ExchangeCredentialsData();
    this.proxyConfig = opts.proxy ?? null;
    this.tentaclesSetupConfig = opts.tentaclesSetupConfig ?? null;
    this.logger = getLogger(`ExchangeManager[${this.exchangeClassString}]`);
  }

  get exchangeType(): ExchangeTypes {
    if (this.isFuture) return ExchangeTypes.FUTURE;
    if (this.isMargin) return ExchangeTypes.MARGIN;
    if (this.isOption) return ExchangeTypes.OPTION;
    if (this.isSpot) return ExchangeTypes.SPOT;
    return ExchangeTypes.UNKNOWN;
  }

  async initialize(): Promise<void> {
    if (!this.exchange) throw new Error("ExchangeManager has no REST exchange wired up");
    await this.exchange.initialize();
    if (this.exchangeWebSocket) {
      await this.exchangeWebSocket.initialize();
    }
    this.isInitialized = true;
    Exchanges.add({ exchangeName: this.exchangeClassString, exchangeManager: this });
  }

  async stop(): Promise<void> {
    if (this.isStopped) return;
    try {
      if (this.exchangeWebSocket) await this.exchangeWebSocket.stop();
    } catch (err) {
      this.logger.exception(err, "Error stopping WebSocket exchange");
    }
    try {
      if (this.exchange) await this.exchange.stop();
    } catch (err) {
      this.logger.exception(err, "Error stopping REST exchange");
    }
    Exchanges.remove(this.exchangeClassString, this.id);
    this.isStopped = true;
  }
}
