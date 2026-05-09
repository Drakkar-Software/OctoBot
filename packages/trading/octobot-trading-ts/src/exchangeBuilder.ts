// Slimmed port of exchange_builder.py. The Python builder coordinates tentacle
// loading, channel registration, and personal_data spinning-up. The browser
// port keeps the fluent API and the wiring step that connects ExchangeManager →
// CCXTConnector → RestExchange → optional WebSocket exchange.

import { ExchangeManager, ExchangeManagerOptions } from "./exchangeManager.js";
import { ExchangeCredentialsData, ExchangeCredentialsDataOptions } from "./config/exchangeCredentialsData.js";
import { ExchangeProxyConfig, ExchangeProxyConfigOptions } from "./config/exchangeProxyConfig.js";
import { CCXTConnector } from "./connectors/ccxt/ccxtConnector.js";
import { CCXTAdapter } from "./adapters/ccxtAdapter.js";
import { RestExchange } from "./types/restExchange.js";
import { DefaultRestExchange } from "./implementations/defaultRestExchange.js";
import { CCXTWebsocketConnector } from "./connectors/ccxt/ccxtWebsocketConnector.js";
import { DefaultWebSocketExchange } from "./implementations/defaultWebsocketExchange.js";

type RestExchangeCtor = new (
  config: Record<string, unknown>,
  exchangeManager: ExchangeManager,
  connector: CCXTConnector,
) => RestExchange;

type WebSocketCtor = new (
  config: Record<string, unknown>,
  exchangeManager: ExchangeManager,
  wsConnector: CCXTWebsocketConnector,
) => DefaultWebSocketExchange;

export class ExchangeBuilder {
  private exchangeName: string;
  private config: Record<string, unknown> = {};
  private credentials: ExchangeCredentialsData = new ExchangeCredentialsData();
  private proxy: ExchangeProxyConfig | null = null;
  private isSpot = true;
  private isFuture = false;
  private isMargin = false;
  private isOption = false;
  private isSandboxed = false;
  private adapterClass: typeof CCXTAdapter = CCXTAdapter;
  private restExchangeClass: RestExchangeCtor = DefaultRestExchange;
  private webSocketClass: WebSocketCtor | null = null;
  private webSocketEnabled = false;
  private additionalCcxtOptions: Record<string, unknown> = {};

  constructor(exchangeName: string) {
    this.exchangeName = exchangeName;
  }

  setConfig(config: Record<string, unknown>): this {
    this.config = config;
    return this;
  }

  setCredentials(opts: ExchangeCredentialsDataOptions | ExchangeCredentialsData): this {
    this.credentials = opts instanceof ExchangeCredentialsData ? opts : new ExchangeCredentialsData(opts);
    return this;
  }

  setProxy(opts: ExchangeProxyConfigOptions | ExchangeProxyConfig): this {
    this.proxy = opts instanceof ExchangeProxyConfig ? opts : new ExchangeProxyConfig(opts);
    return this;
  }

  asSpot(): this {
    this.isSpot = true; this.isFuture = false; this.isMargin = false; this.isOption = false;
    return this;
  }

  asFuture(): this {
    this.isFuture = true; this.isSpot = false; this.isMargin = false; this.isOption = false;
    return this;
  }

  asMargin(): this {
    this.isMargin = true; this.isSpot = false; this.isFuture = false; this.isOption = false;
    return this;
  }

  asOption(): this {
    this.isOption = true; this.isSpot = false; this.isFuture = false; this.isMargin = false;
    return this;
  }

  setSandboxed(sandboxed = true): this {
    this.isSandboxed = sandboxed;
    return this;
  }

  setAdapterClass(adapterClass: typeof CCXTAdapter): this {
    this.adapterClass = adapterClass;
    return this;
  }

  setRestExchangeClass(klass: RestExchangeCtor): this {
    this.restExchangeClass = klass;
    return this;
  }

  setWebSocketClass(klass: WebSocketCtor): this {
    this.webSocketClass = klass;
    this.webSocketEnabled = true;
    return this;
  }

  enableWebSocket(enabled = true): this {
    this.webSocketEnabled = enabled;
    return this;
  }

  setCcxtOptions(opts: Record<string, unknown>): this {
    this.additionalCcxtOptions = opts;
    return this;
  }

  build(): ExchangeManager {
    const opts: ExchangeManagerOptions = {
      exchangeClassString: this.exchangeName,
      config: this.config,
      isSpot: this.isSpot,
      isFuture: this.isFuture,
      isMargin: this.isMargin,
      isOption: this.isOption,
      isSandboxed: this.isSandboxed,
      credentials: this.credentials,
      proxy: this.proxy ?? undefined,
      webSocketEnabled: this.webSocketEnabled,
    };
    const manager = new ExchangeManager(opts);

    const connector = new CCXTConnector(this.config, manager, {
      adapterClass: this.adapterClass,
      additionalConfig: { options: this.additionalCcxtOptions },
    });
    const ExchangeClass = this.restExchangeClass;
    manager.exchange = new ExchangeClass(this.config, manager, connector);

    if (this.webSocketEnabled) {
      const WSClass = this.webSocketClass ?? DefaultWebSocketExchange;
      const wsConnector = new CCXTWebsocketConnector(this.config, manager);
      manager.exchangeWebSocket = new WSClass(this.config, manager, wsConnector);
    }

    return manager;
  }
}

export function createExchangeBuilderInstance(exchangeName: string): ExchangeBuilder {
  return new ExchangeBuilder(exchangeName);
}
