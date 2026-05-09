import Decimal from "decimal.js";
import { SymbolDetails, makeSymbolDetails } from "./symbolDetails.js";
import {
  PRICE_INDEX_TIME,
  PRICE_INDEX_OPEN,
  PRICE_INDEX_HIGH,
  PRICE_INDEX_LOW,
  PRICE_INDEX_CLOSE,
  PRICE_INDEX_VOL,
} from "../adapters/ccxtAdapter.js";

export interface IncompatibleAssetDetails {
  symbol: string;
  updatedAt: number;
}

export interface ExchangeAuthDetails {
  apiKey: string;
  apiSecret: string;
  apiPassword: string;
  accessToken: string;
  exchangeType: string;
  sandboxed: boolean;
  brokerEnabled: boolean;
  encrypted: string;
  exchangeAccountId: string | null;
  exchangeCredentialId: string | null;
  incompatibleAssets: IncompatibleAssetDetails[] | null;
}

export interface ExchangeDetailsData {
  name: string;
}

export class MarketDetails {
  id = "";
  symbol = "";
  details: SymbolDetails = makeSymbolDetails();
  timeFrame = "";
  close: number[] = [];
  open: number[] = [];
  high: number[] = [];
  low: number[] = [];
  volume: number[] = [];
  time: number[] = [];

  hasFullCandles(): boolean {
    return (
      this.close.length > 0 &&
      this.open.length > 0 &&
      this.high.length > 0 &&
      this.low.length > 0 &&
      this.time.length > 0
    );
  }

  formatCandle(index: number): number[] {
    const ohlcv = new Array(6).fill(0);
    ohlcv[PRICE_INDEX_TIME] = this.time[index];
    ohlcv[PRICE_INDEX_OPEN] = this.open[index];
    ohlcv[PRICE_INDEX_HIGH] = this.high[index];
    ohlcv[PRICE_INDEX_LOW] = this.low[index];
    ohlcv[PRICE_INDEX_CLOSE] = this.close[index];
    ohlcv[PRICE_INDEX_VOL] = this.volume[index];
    return ohlcv;
  }

  getFormattedCandles(): number[][] {
    return Array.from({ length: this.close.length }, (_, i) => this.formatCandle(i));
  }

  static fromOhlcvs(symbol: string, timeFrame: string, ohlcvs: number[][]): MarketDetails {
    const m = new MarketDetails();
    m.symbol = symbol;
    m.timeFrame = timeFrame;
    m.close = ohlcvs.map((o) => o[PRICE_INDEX_CLOSE]);
    m.open = ohlcvs.map((o) => o[PRICE_INDEX_OPEN]);
    m.high = ohlcvs.map((o) => o[PRICE_INDEX_HIGH]);
    m.low = ohlcvs.map((o) => o[PRICE_INDEX_LOW]);
    m.volume = ohlcvs.map((o) => o[PRICE_INDEX_VOL]);
    m.time = ohlcvs.map((o) => o[PRICE_INDEX_TIME]);
    return m;
  }
}

export interface OrdersDetails {
  openOrders: Record<string, unknown>[];
  missingOrders: Record<string, unknown>[];
}

export interface PortfolioDetails {
  initialValue: number;
  content: Record<string, Record<string, number | Decimal>>;
  fullContent: Record<string, Record<string, number | Decimal>>;
  assetValues: Record<string, number>;
}

export interface PositionDetails {
  position: Record<string, unknown>;
  contract: Record<string, unknown>;
}

export class ExchangeData {
  authDetails: ExchangeAuthDetails = {
    apiKey: "",
    apiSecret: "",
    apiPassword: "",
    accessToken: "",
    exchangeType: "",
    sandboxed: false,
    brokerEnabled: false,
    encrypted: "",
    exchangeAccountId: null,
    exchangeCredentialId: null,
    incompatibleAssets: [],
  };
  exchangeDetails: ExchangeDetailsData = { name: "" };
  markets: MarketDetails[] = [];
  portfolioDetails: PortfolioDetails = {
    initialValue: 0,
    content: {},
    fullContent: {},
    assetValues: {},
  };
  ordersDetails: OrdersDetails = { openOrders: [], missingOrders: [] };
  trades: Record<string, unknown>[] = [];
  positions: PositionDetails[] = [];

  getPrice(symbol: string): number {
    for (const market of this.markets) {
      if (market.symbol === symbol) return market.close[market.close.length - 1];
    }
    throw new Error(`Symbol not found in exchange data: ${symbol}`);
  }
}

export function exchangeDataFactory(
  exchangeInternalName: string,
  exchangeType?: string,
  sandboxed = false,
  exchangeCredentialId?: string,
  authDetails?: Partial<ExchangeAuthDetails>,
): ExchangeData {
  const data = new ExchangeData();
  data.exchangeDetails.name = exchangeInternalName;
  data.authDetails.sandboxed = sandboxed;
  data.authDetails.exchangeCredentialId = exchangeCredentialId ?? null;
  if (exchangeType) data.authDetails.exchangeType = exchangeType;
  if (authDetails) Object.assign(data.authDetails, authDetails);
  return data;
}
