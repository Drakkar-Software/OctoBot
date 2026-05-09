// Slimmed port of config/exchange_proxy_config.py. Most of the Python file
// builds Python aiohttp proxy callbacks; in the browser the user agent or a
// service worker is responsible for routing — we keep proxy URLs as plain
// configuration that callers can pass to ccxt.

export interface ExchangeProxyConfigOptions {
  httpProxy?: string;
  httpsProxy?: string;
  socksProxy?: string;
  wsProxy?: string;
  wssProxy?: string;
  wsSocksProxy?: string;
  useAuthenticatedExchangeRequestsOnlyProxy?: boolean;
}

export class ExchangeProxyConfig {
  httpProxy: string | null = null;
  httpsProxy: string | null = null;
  socksProxy: string | null = null;
  wsProxy: string | null = null;
  wssProxy: string | null = null;
  wsSocksProxy: string | null = null;
  useAuthenticatedExchangeRequestsOnlyProxy = false;

  constructor(opts: ExchangeProxyConfigOptions = {}) {
    this.httpProxy = opts.httpProxy ?? null;
    this.httpsProxy = opts.httpsProxy ?? null;
    this.socksProxy = opts.socksProxy ?? null;
    this.wsProxy = opts.wsProxy ?? null;
    this.wssProxy = opts.wssProxy ?? null;
    this.wsSocksProxy = opts.wsSocksProxy ?? null;
    this.useAuthenticatedExchangeRequestsOnlyProxy = !!opts.useAuthenticatedExchangeRequestsOnlyProxy;
  }

  hasRestProxy(): boolean {
    return !!(this.httpProxy || this.httpsProxy || this.socksProxy);
  }

  hasWebsocketProxy(): boolean {
    return !!(this.wsProxy || this.wssProxy || this.wsSocksProxy);
  }
}
