// Mirror of util/exchange_data_util.py — the Python file is small and only
// holds factory helpers that recreate ExchangeData/MarketDetails from raw dicts.

import { ExchangeData, MarketDetails } from "./exchangeData.js";

export function rebuildMarketDetails(raw: Partial<MarketDetails>): MarketDetails {
  const m = new MarketDetails();
  Object.assign(m, raw);
  return m;
}

export function rebuildExchangeData(raw: Partial<ExchangeData>): ExchangeData {
  const data = new ExchangeData();
  Object.assign(data, raw);
  if (Array.isArray(data.markets)) {
    data.markets = data.markets.map((m) =>
      m instanceof MarketDetails ? m : rebuildMarketDetails(m as Partial<MarketDetails>),
    );
  }
  return data;
}
