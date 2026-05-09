// Mirror of exchange_details.py — the dataclass is tiny.

export interface ExchangeDetails {
  id: string;
  name: string;
  url: string;
  api: string;
  logoUrl: string;
  hasWebsocket: boolean;
}
