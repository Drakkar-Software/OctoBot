// Subset port of octobot_commons.proxy_config — the base ProxyConfig that
// trading-side ExchangeProxyConfig extends. Browser code mostly passes proxy
// URLs through to ccxt so we keep the data-bag shape and skip the runtime
// callbacks.

export const DEFAULT_PROXY_HOST = "";

export interface ProxyConfigOptions {
  httpProxy?: string | null;
  httpsProxy?: string | null;
  socksProxy?: string | null;
  wsProxy?: string | null;
  wssProxy?: string | null;
  wsSocksProxy?: string | null;
}

export class ProxyConfig {
  httpProxy: string | null = null;
  httpsProxy: string | null = null;
  socksProxy: string | null = null;
  wsProxy: string | null = null;
  wssProxy: string | null = null;
  wsSocksProxy: string | null = null;
  proxyHost: string = DEFAULT_PROXY_HOST;

  constructor(opts: ProxyConfigOptions = {}) {
    this.httpProxy = opts.httpProxy ?? null;
    this.httpsProxy = opts.httpsProxy ?? null;
    this.socksProxy = opts.socksProxy ?? null;
    this.wsProxy = opts.wsProxy ?? null;
    this.wssProxy = opts.wssProxy ?? null;
    this.wsSocksProxy = opts.wsSocksProxy ?? null;
  }

  hasRestProxy(): boolean {
    return !!(this.httpProxy || this.httpsProxy || this.socksProxy);
  }

  hasWebsocketProxy(): boolean {
    return !!(this.wsProxy || this.wssProxy || this.wsSocksProxy);
  }
}
