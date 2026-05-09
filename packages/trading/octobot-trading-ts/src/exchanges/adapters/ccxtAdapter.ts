import Decimal from "decimal.js";
import { AbstractAdapter, RawDict } from "./abstractAdapter.js";
import {
  ExchangeConstantsTickersColumns as ETC,
  ExchangeConstantsOrderColumns as EOC,
  ExchangeConstantsOrderBookInfoColumns as EOBC,
  ExchangeConstantsMarketStatusColumns as EMSC,
  ExchangeConstantsPositionColumns as EPC,
  ExchangeConstantsFundingColumns as EFC,
  TradeOrderType,
  PositionMode,
  PositionSide,
  MarginType,
  FeePropertyColumns,
} from "../enums.js";
import { ZERO, ONE, toDecimal } from "../util/decimalUtil.js";

// PriceIndexes mirror octobot_commons.enums.PriceIndexes — fixed positions in
// CCXT-style OHLCV arrays.
export const PRICE_INDEX_TIME = 0;
export const PRICE_INDEX_OPEN = 1;
export const PRICE_INDEX_HIGH = 2;
export const PRICE_INDEX_LOW = 3;
export const PRICE_INDEX_CLOSE = 4;
export const PRICE_INDEX_VOL = 5;

const TIMEFRAME_TO_SECONDS: Record<string, number> = {
  "1m": 60,
  "3m": 180,
  "5m": 300,
  "15m": 900,
  "30m": 1800,
  "1h": 3600,
  "2h": 7200,
  "4h": 14400,
  "6h": 21600,
  "8h": 28800,
  "12h": 43200,
  "1d": 86400,
  "3d": 259200,
  "1w": 604800,
  "1M": 2592000,
};

function getDigitsCount(value: number | null | undefined): number {
  if (value === null || value === undefined) return 0;
  if (Number.isInteger(value)) return Number(value);
  // Match octobot_commons.number_util.get_digits_count
  const s = value.toString();
  if (s.includes("e-")) {
    const [, exp] = s.split("e-");
    return parseInt(exp, 10);
  }
  if (s.includes(".")) {
    return s.split(".")[1].length;
  }
  return 0;
}

export class CCXTAdapter extends AbstractAdapter {
  fixOrder(raw: RawDict, opts: RawDict = {}): RawDict {
    const fixed = super.fixOrder(raw, opts);
    try {
      const exchangeTimestamp = fixed[EOC.TIMESTAMP] as number | undefined;
      if (exchangeTimestamp !== undefined) {
        fixed[EOC.TIMESTAMP] = this.getUniformizedTimestamp(exchangeTimestamp);
      }
      this.adaptQuantitiesWithContractSize(fixed, opts.symbol as string | undefined);
    } catch (e) {
      this.logger.error(`Fail to cleanup order dict (${(e as Error).message})`);
    }
    this.registerExchangeFees(fixed);
    return fixed;
  }

  parseOrder(fixed: RawDict, _opts: RawDict = {}): RawDict {
    return fixed;
  }

  adaptAmountFromFilledOrCost(fixed: RawDict): void {
    if (
      fixed[EOC.TYPE] === TradeOrderType.MARKET &&
      fixed[EOC.SIDE] === "buy" &&
      fixed[EOC.FILLED]
    ) {
      fixed[EOC.AMOUNT] = fixed[EOC.FILLED];
    }
    if (
      !fixed[EOC.AMOUNT] &&
      fixed[EOC.COST] &&
      fixed[EOC.PRICE]
    ) {
      const cost = Number(fixed[EOC.COST]);
      const price = Number(fixed[EOC.PRICE]);
      if (price !== 0) fixed[EOC.AMOUNT] = cost / price;
    }
  }

  adaptQuantitiesWithContractSize(orderOrTrade: RawDict, symbol?: string): void {
    // Forward-declared connector exposes is_future / get_contract_size when
    // running under a futures exchange. Browser callers commonly hit spot only,
    // so we no-op gracefully when the connector doesn't support futures.
    type FutureCapable = {
      exchangeManager?: { isFuture?: boolean };
      getContractSize?: (s: string) => Decimal;
    };
    const c = this.connector as FutureCapable | null;
    if (!c?.exchangeManager?.isFuture || !c.getContractSize) return;

    const usedSymbol = symbol || (orderOrTrade[EOC.SYMBOL] as string | undefined);
    if (!usedSymbol) return;
    const contractSize = c.getContractSize(usedSymbol);
    if (contractSize.eq(ONE)) return;

    const cs = contractSize.toNumber();
    const amount = orderOrTrade[EOC.AMOUNT];
    if (amount) orderOrTrade[EOC.AMOUNT] = Number(amount) * cs;
    const filled = orderOrTrade[EOC.FILLED];
    if (filled) orderOrTrade[EOC.FILLED] = Number(filled) * cs;
  }

  protected registerExchangeFees(orderOrTrade: RawDict): void {
    const fees = orderOrTrade[EOC.FEE] as RawDict | undefined;
    if (fees && typeof fees === "object") {
      fees[FeePropertyColumns.EXCHANGE_ORIGINAL_COST] = fees[FeePropertyColumns.COST];
      fees[FeePropertyColumns.IS_FROM_EXCHANGE] = true;
    }
  }

  protected ensureFees(orderOrTrade: RawDict): void {
    if (orderOrTrade[EOC.FEE] === null || orderOrTrade[EOC.FEE] === undefined) {
      orderOrTrade[EOC.FEE] = {
        [FeePropertyColumns.COST]: ZERO,
        [FeePropertyColumns.EXCHANGE_ORIGINAL_COST]: ZERO,
        [FeePropertyColumns.CURRENCY]: null,
        [FeePropertyColumns.RATE]: null,
        [FeePropertyColumns.TYPE]: "takerOrMaker",
        [FeePropertyColumns.IS_FROM_EXCHANGE]: true,
      };
    }
  }

  protected fixOhlcvPrices(ohlcv: number[]): void {
    for (let i = PRICE_INDEX_TIME + 1; i < ohlcv.length; i++) {
      ohlcv[i] = Number(ohlcv[i]);
    }
  }

  fixOhlcv(raw: RawDict, opts: RawDict = {}): RawDict {
    const arr = raw as unknown as number[][];
    const tf = opts.timeFrame as string | undefined;
    const candleSeconds = tf && TIMEFRAME_TO_SECONDS[tf] ? TIMEFRAME_TO_SECONDS[tf] : 1;
    for (let i = 0; i < arr.length; i++) {
      const row = arr[i];
      const ts = this.getUniformizedTimestamp(row[PRICE_INDEX_TIME]) ?? 0;
      const intVal = Math.trunc(ts);
      row[PRICE_INDEX_TIME] = intVal - (intVal % candleSeconds);
      this.fixOhlcvPrices(row);
    }
    return raw;
  }

  parseOhlcv(fixed: RawDict, _opts: RawDict = {}): RawDict[] {
    return fixed as unknown as RawDict[];
  }

  fixKline(raw: RawDict, opts: RawDict = {}): RawDict {
    return this.fixOhlcv(raw, opts);
  }

  parseKline(fixed: RawDict, _opts: RawDict = {}): RawDict {
    return fixed;
  }

  fixTicker(raw: RawDict, opts: RawDict = {}): RawDict {
    const fixed = super.fixTicker(raw, opts);
    const ts = fixed[ETC.TIMESTAMP] as number | undefined;
    if (ts) {
      fixed[ETC.TIMESTAMP] = Math.trunc(this.getUniformizedTimestamp(ts) ?? 0);
    }
    return fixed;
  }

  parseTicker(fixed: RawDict, _opts: RawDict = {}): RawDict {
    return fixed;
  }

  createTickerFromKline(kline: RawDict, symbol: string, _opts: RawDict = {}): RawDict {
    const k = kline as unknown as number[];
    return {
      [ETC.SYMBOL]: symbol,
      [ETC.TIMESTAMP]: k[PRICE_INDEX_TIME],
      [ETC.OPEN]: k[PRICE_INDEX_OPEN],
      [ETC.HIGH]: k[PRICE_INDEX_HIGH],
      [ETC.LOW]: k[PRICE_INDEX_LOW],
      [ETC.CLOSE]: k[PRICE_INDEX_CLOSE],
      [ETC.BASE_VOLUME]: k[PRICE_INDEX_VOL],
      [ETC.LAST]: k[PRICE_INDEX_CLOSE],
      [ETC.BID]: null,
      [ETC.BID_VOLUME]: null,
      [ETC.ASK]: null,
      [ETC.ASK_VOLUME]: null,
      [ETC.PREVIOUS_CLOSE]: null,
    };
  }

  parseBalance(fixed: RawDict, _opts: RawDict = {}): RawDict {
    delete fixed["free"];
    delete fixed["used"];
    delete fixed["total"];
    delete fixed["info"];
    delete fixed["datetime"];
    delete fixed["timestamp"];
    // Convert per-currency balances to Decimal-keyed structure.
    const out: RawDict = {};
    for (const [currency, value] of Object.entries(fixed)) {
      if (typeof value === "object" && value !== null) {
        const v = value as RawDict;
        out[currency] = {
          available: toDecimal(v.free as string | number | null | undefined),
          used: toDecimal(v.used as string | number | null | undefined),
          total: toDecimal(v.total as string | number | null | undefined),
        };
      }
    }
    return out;
  }

  fixOrderBook(raw: RawDict, opts: RawDict = {}): RawDict {
    const fixed = super.fixOrderBook(raw, opts);
    const exchangeTimestamp = fixed[EOBC.TIMESTAMP] as number | null | undefined;
    if (exchangeTimestamp === null || exchangeTimestamp === undefined) {
      type CurrentTimeCapable = { getExchangeCurrentTime?: () => number };
      const c = this.connector as CurrentTimeCapable | null;
      fixed[EOBC.TIMESTAMP] = c?.getExchangeCurrentTime ? c.getExchangeCurrentTime() : Date.now() / 1000;
    } else {
      fixed[EOBC.TIMESTAMP] = this.getUniformizedTimestamp(exchangeTimestamp);
    }
    return fixed;
  }

  parseOrderBook(fixed: RawDict, _opts: RawDict = {}): RawDict {
    return fixed;
  }

  fixPublicRecentTrades(raw: RawDict[], _opts: RawDict = {}): RawDict[] {
    for (const t of raw) {
      const ts = t[EOC.TIMESTAMP] as number | undefined;
      if (ts !== undefined) t[EOC.TIMESTAMP] = this.getUniformizedTimestamp(ts);
    }
    return raw;
  }

  parsePublicRecentTrades(fixed: RawDict[], _opts: RawDict = {}): RawDict[] {
    for (const t of fixed) {
      delete t[EOC.INFO];
      delete t[EOC.DATETIME];
      delete t[EOC.EXCHANGE_ID];
      delete t[EOC.ID];
      delete t[EOC.ORDER];
      delete t[EOC.FEE];
      delete t[EOC.TYPE];
      delete t[EOC.TAKER_OR_MAKER];
    }
    return fixed;
  }

  fixTrades(raw: RawDict[], opts: RawDict = {}): RawDict[] {
    const fixed = super.fixTrades(raw, opts);
    for (const trade of fixed) {
      const ts = trade[EOC.TIMESTAMP] as number | undefined;
      if (ts !== undefined) trade[EOC.TIMESTAMP] = this.getUniformizedTimestamp(ts);
      trade[EOC.EXCHANGE_ID] = trade[EOC.ORDER];
      if (trade[EOC.TYPE] === null || trade[EOC.TYPE] === undefined) {
        trade[EOC.TYPE] = trade[EOC.TAKER_OR_MAKER] === "taker"
          ? TradeOrderType.MARKET
          : TradeOrderType.LIMIT;
      }
      this.adaptQuantitiesWithContractSize(trade);
      this.registerExchangeFees(trade);
    }
    return fixed;
  }

  parseTrades(fixed: RawDict[], _opts: RawDict = {}): RawDict[] {
    return fixed;
  }

  parsePosition(fixed: RawDict, opts: RawDict = {}): RawDict {
    const forceEmpty = !!opts.forceEmpty;
    const originalSide = fixed["side"];
    const symbol = fixed["symbol"] as string | undefined;
    const contractSize = toDecimal((fixed["contractSize"] as number | string | null) ?? 0);
    const contracts = forceEmpty ? ZERO : toDecimal((fixed["contracts"] as number | string | null) ?? 0);
    const isEmpty = contracts.eq(ZERO);
    const positionMode = fixed["hedged"] ? PositionMode.HEDGE : PositionMode.ONE_WAY;

    const positionSide = positionMode === PositionMode.HEDGE
      ? (originalSide === PositionSide.LONG ? PositionSide.LONG : PositionSide.SHORT)
      : PositionSide.BOTH;

    let liquidationPriceRaw = fixed["liquidationPrice"];
    if (forceEmpty || liquidationPriceRaw === null || liquidationPriceRaw === undefined) {
      liquidationPriceRaw = ZERO;
    }
    const liquidationPrice = liquidationPriceRaw instanceof Decimal
      ? liquidationPriceRaw
      : toDecimal(liquidationPriceRaw as string | number);

    const marginTypeRaw = (fixed["marginType"] || fixed["marginMode"]) as string | undefined;
    const marginType = marginTypeRaw
      ? (Object.values(MarginType) as string[]).includes(marginTypeRaw)
        ? (marginTypeRaw as MarginType)
        : null
      : null;

    type ContractTypeCapable = {
      exchangeManager?: { exchange?: { getContractType?: (s: string) => unknown } };
    };
    const c = this.connector as ContractTypeCapable | null;
    const contractType = symbol && c?.exchangeManager?.exchange?.getContractType
      ? c.exchangeManager.exchange.getContractType(symbol)
      : null;

    const dec = (v: unknown): Decimal => isEmpty ? ZERO : toDecimal((v as string | number | null) ?? 0);

    return {
      ...fixed,
      [EPC.SYMBOL]: symbol,
      [EPC.TIMESTAMP]: fixed["timestamp"] ?? Date.now() / 1000,
      [EPC.SIDE]: positionSide,
      [EPC.MARGIN_TYPE]: marginType,
      [EPC.SIZE]: originalSide === PositionSide.LONG
        ? contractSize.mul(contracts)
        : contractSize.mul(contracts).neg(),
      [EPC.CONTRACT_TYPE]: contractType,
      [EPC.LEVERAGE]: this.safeDecimal(fixed, "leverage", ONE),
      [EPC.POSITION_MODE]: positionMode,
      [EPC.COLLATERAL]: dec(fixed["collateral"]),
      [EPC.NOTIONAL]: dec(fixed["notional"]),
      [EPC.INITIAL_MARGIN]: dec(fixed["initialMargin"]),
      [EPC.AUTO_DEPOSIT_MARGIN]: false,
      [EPC.UNREALIZED_PNL]: dec(fixed["unrealizedPnl"]),
      [EPC.REALISED_PNL]: dec(fixed["realizedPnl"]),
      [EPC.LIQUIDATION_PRICE]: liquidationPrice,
      [EPC.MARK_PRICE]: dec(fixed["markPrice"]),
      [EPC.ENTRY_PRICE]: dec(fixed["entryPrice"]),
    };
  }

  parseFundingRate(fixed: RawDict, _opts: RawDict = {}): RawDict {
    return {
      ...fixed,
      [EFC.FUNDING_RATE]: this.safeDecimal(fixed, "fundingRate", new Decimal(NaN)),
      [EFC.LAST_FUNDING_TIME]: this.getUniformizedTimestamp(
        (fixed["previousFundingTimestamp"] as number) || 0,
      ),
      [EFC.PREDICTED_FUNDING_RATE]: this.safeDecimal(fixed, "fundingRate", new Decimal(NaN)),
      [EFC.NEXT_FUNDING_TIME]: this.getUniformizedTimestamp(
        (fixed["fundingTimestamp"] as number) || 0,
      ),
    };
  }

  parseLeverage(fixed: RawDict, _opts: RawDict = {}): RawDict {
    return fixed;
  }

  parseFundingRateHistory(fixed: RawDict[], _opts: RawDict = {}): RawDict[] {
    return fixed;
  }

  parseLeverageTiers(fixed: RawDict, _opts: RawDict = {}): Record<string, RawDict[]> {
    const out: Record<string, RawDict[]> = {};
    for (const [symbol, tiers] of Object.entries(fixed)) {
      out[symbol] = (tiers as RawDict[]).map((tier: RawDict) => ({
        tier: tier["tier"],
        currency: tier["currency"],
        min_notional: tier["minNotional"],
        max_notional: tier["maxNotional"],
        maintenance_margin_rate: tier["maintenanceMarginRate"],
        max_leverage: tier["maxLeverage"],
      }));
    }
    return out;
  }

  parseMarkPrice(fixed: RawDict, _opts: RawDict = {}): RawDict {
    return fixed;
  }

  fixMarketStatus(raw: RawDict, removePriceLimits = false, opts: RawDict = {}): RawDict {
    const fixed = super.fixMarketStatus(raw, removePriceLimits, opts);
    if (!fixed || Object.keys(fixed).length === 0) return fixed;
    const precision = fixed[EMSC.PRECISION] as RawDict | undefined;
    if (precision) {
      precision[EMSC.PRECISION_AMOUNT] = getDigitsCount(precision[EMSC.PRECISION_AMOUNT] as number);
      precision[EMSC.PRECISION_PRICE] = getDigitsCount(precision[EMSC.PRECISION_PRICE] as number);
    }
    if (removePriceLimits) {
      const limits = fixed[EMSC.LIMITS] as RawDict | undefined;
      const priceLimits = limits?.[EMSC.LIMITS_PRICE] as RawDict | undefined;
      if (priceLimits) {
        priceLimits[EMSC.LIMITS_PRICE_MIN] = null;
        priceLimits[EMSC.LIMITS_PRICE_MAX] = null;
      }
    }
    return fixed;
  }

  parseMarketStatus(fixed: RawDict, _removePriceLimits = false, _opts: RawDict = {}): RawDict {
    return fixed;
  }

  parseTransaction(fixed: RawDict, _opts: RawDict = {}): RawDict {
    return {
      id: fixed["id"],
      txid: fixed["txid"],
      timestamp: fixed["timestamp"],
      address_from: fixed["address_from"] ?? fixed["addressFrom"],
      address_to: fixed["address_to"] ?? fixed["addressTo"],
      tag: fixed["tag"],
      type: fixed["type"],
      amount: toDecimal((fixed["amount"] as string | number | null) ?? 0),
      currency: fixed["currency"],
      status: fixed["status"],
      fee: fixed["fee"],
      network: fixed["network"],
      comment: fixed["comment"],
      internal: fixed["internal"],
    };
  }

  parseDepositAddress(fixed: RawDict, _opts: RawDict = {}): RawDict {
    return {
      currency: fixed["currency"],
      network: fixed["network"],
      address: fixed["address"],
      tag: fixed["tag"],
    };
  }
}
