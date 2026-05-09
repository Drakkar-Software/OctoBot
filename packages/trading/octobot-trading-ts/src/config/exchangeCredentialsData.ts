// Mirror of config/exchange_credentials_data.py.

export interface ExchangeCredentialsDataOptions {
  apiKey?: string | null;
  secret?: string | null;
  password?: string | null;
  uid?: string | null;
  authToken?: string | null;
  authTokenHeaderPrefix?: string | null;
  walletAddress?: string | null;
  privateKey?: string | null;
}

export class ExchangeCredentialsData {
  apiKey: string | null = null;
  secret: string | null = null;
  password: string | null = null;
  uid: string | null = null;
  authToken: string | null = null;
  authTokenHeaderPrefix: string | null = null;
  walletAddress: string | null = null;
  privateKey: string | null = null;

  constructor(opts: ExchangeCredentialsDataOptions = {}) {
    this.apiKey = opts.apiKey ?? null;
    this.secret = opts.secret ?? null;
    this.password = opts.password ?? null;
    this.uid = opts.uid ?? null;
    this.authToken = opts.authToken ?? null;
    this.authTokenHeaderPrefix = opts.authTokenHeaderPrefix ?? null;
    this.walletAddress = opts.walletAddress ?? null;
    this.privateKey = opts.privateKey ?? null;
  }

  hasCredentials(): boolean {
    return !!((this.apiKey && this.secret) || (this.walletAddress && this.privateKey));
  }
}
