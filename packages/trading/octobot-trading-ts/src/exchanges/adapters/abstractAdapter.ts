import { ExchangeConstantsOrderColumns, OrderStatus } from "../enums.js";
import { UnexpectedAdapterError } from "../errors.js";
import { Logger, getLogger } from "../util/logger.js";
import { toDecimal } from "../util/decimalUtil.js";
import Decimal from "decimal.js";

const MSECONDS_TO_SECONDS = 1000;
const FUTURE_TIMESTAMP_THRESHOLD = 16728292300; // matches commons_constants

// Mirrors the @_adapter decorator from abstract_adapter.py: short-circuits when
// the input is null/undefined and wraps any thrown error in UnexpectedAdapterError.
function adapter<TIn, TOut, A extends unknown[]>(
  fn: (raw: TIn, ...args: A) => TOut,
): (raw: TIn | null | undefined, ...args: A) => TOut | null {
  return function wrapped(this: AbstractAdapter, raw, ...args) {
    if (raw === null || raw === undefined) return null;
    try {
      return fn.call(this, raw, ...args);
    } catch (err) {
      throw new UnexpectedAdapterError(
        `Unexpected error when adapting exchange data: ${(err as Error).message} (data: ${JSON.stringify(raw)})`,
      );
    }
  } as (raw: TIn | null | undefined, ...args: A) => TOut | null;
}

// Adapter inputs/outputs are loose dictionaries from CCXT, so we use generic
// records for the public API. Subclasses can narrow further via TypedDict-style
// interfaces if they want.
export type RawDict = Record<string, unknown>;

export interface AdaptOrdersOptions {
  cancelledOnly?: boolean;
  [key: string]: unknown;
}

export class AbstractAdapter {
  protected logger: Logger;
  // typed loosely on purpose — `Connector` is forward-declared and may be a
  // CCXTConnector or a custom one.
  constructor(public connector: unknown) {
    this.logger = getLogger(this.constructor.name);
  }

  // ---- adapt_*: orchestration shells (decorator + fix → parse) ----

  adaptOrders(raw: RawDict[] | null | undefined, opts: AdaptOrdersOptions = {}): RawDict[] {
    if (raw === null || raw === undefined) return [];
    try {
      const result: RawDict[] = [];
      for (const element of raw) {
        const adapted = this.adaptOrder(element, opts);
        if (!opts.cancelledOnly || !adapted ||
            adapted[ExchangeConstantsOrderColumns.STATUS] === OrderStatus.CANCELED) {
          if (adapted) result.push(adapted);
        }
      }
      return result;
    } catch (err) {
      throw new UnexpectedAdapterError(
        `Unexpected error when adapting orders: ${(err as Error).message}`,
      );
    }
  }

  adaptOrder = adapter<RawDict, RawDict, [opts?: RawDict]>(function (
    this: AbstractAdapter,
    raw,
    opts = {},
  ) {
    const fixed = this.fixOrder(raw, opts);
    return this.parseOrder(fixed, opts);
  });

  adaptOhlcv = adapter<RawDict, RawDict[], [opts?: RawDict]>(function (
    this: AbstractAdapter,
    raw,
    opts = {},
  ) {
    const fixed = this.fixOhlcv(raw, opts);
    return this.parseOhlcv(fixed, opts);
  });

  adaptKline = adapter<RawDict, RawDict, [opts?: RawDict]>(function (
    this: AbstractAdapter,
    raw,
    opts = {},
  ) {
    const fixed = this.fixKline(raw, opts);
    return this.parseKline(fixed, opts);
  });

  adaptTicker = adapter<RawDict, RawDict, [opts?: RawDict]>(function (
    this: AbstractAdapter,
    raw,
    opts = {},
  ) {
    const fixed = this.fixTicker(raw, opts);
    return this.parseTicker(fixed, opts);
  });

  adaptTickerFromKline = adapter<RawDict, RawDict, [symbol: string, opts?: RawDict]>(function (
    this: AbstractAdapter,
    raw,
    symbol,
    opts = {},
  ) {
    const fixed = this.createTickerFromKline(raw, symbol, opts);
    return this.parseTicker(fixed, opts);
  });

  adaptBalance = adapter<RawDict, RawDict, [opts?: RawDict]>(function (
    this: AbstractAdapter,
    raw,
    opts = {},
  ) {
    const fixed = this.fixBalance(raw, opts);
    return this.parseBalance(fixed, opts);
  });

  adaptOrderBook = adapter<RawDict, RawDict, [opts?: RawDict]>(function (
    this: AbstractAdapter,
    raw,
    opts = {},
  ) {
    const fixed = this.fixOrderBook(raw, opts);
    return this.parseOrderBook(fixed, opts);
  });

  adaptPublicRecentTrades = adapter<RawDict[], RawDict[], [opts?: RawDict]>(function (
    this: AbstractAdapter,
    raw,
    opts = {},
  ) {
    const fixed = this.fixPublicRecentTrades(raw, opts);
    return this.parsePublicRecentTrades(fixed, opts);
  });

  adaptTrades = adapter<RawDict[], RawDict[], [opts?: RawDict]>(function (
    this: AbstractAdapter,
    raw,
    opts = {},
  ) {
    const fixed = this.fixTrades(raw, opts);
    return this.parseTrades(fixed, opts);
  });

  adaptPosition = adapter<RawDict, RawDict, [opts?: RawDict]>(function (
    this: AbstractAdapter,
    raw,
    opts = {},
  ) {
    const fixed = this.fixPosition(raw, opts);
    return this.parsePosition(fixed, opts);
  });

  adaptFundingRate = adapter<RawDict, RawDict, [opts?: RawDict]>(function (
    this: AbstractAdapter,
    raw,
    opts = {},
  ) {
    const fixed = this.fixFundingRate(raw, opts);
    return this.parseFundingRate(fixed, opts);
  });

  adaptLeverageTiers = adapter<RawDict, Record<string, RawDict[]>, [opts?: RawDict]>(function (
    this: AbstractAdapter,
    raw,
    opts = {},
  ) {
    const fixed = this.fixLeverageTiers(raw, opts);
    return this.parseLeverageTiers(fixed, opts);
  });

  adaptLeverage = adapter<RawDict, RawDict, [opts?: RawDict]>(function (
    this: AbstractAdapter,
    raw,
    opts = {},
  ) {
    const fixed = this.fixLeverage(raw, opts);
    return this.parseLeverage(fixed, opts);
  });

  adaptFundingRateHistory = adapter<RawDict[], RawDict[], [opts?: RawDict]>(function (
    this: AbstractAdapter,
    raw,
    opts = {},
  ) {
    const fixed = this.fixFundingRateHistory(raw, opts);
    return this.parseFundingRateHistory(fixed, opts);
  });

  adaptMarkPrice = adapter<RawDict, RawDict, [opts?: RawDict]>(function (
    this: AbstractAdapter,
    raw,
    opts = {},
  ) {
    const fixed = this.fixMarkPrice(raw, opts);
    return this.parseMarkPrice(fixed, opts);
  });

  adaptMarketStatus = adapter<RawDict, RawDict, [removePriceLimits?: boolean, opts?: RawDict]>(
    function (this: AbstractAdapter, raw, removePriceLimits = false, opts = {}) {
      const fixed = this.fixMarketStatus(raw, removePriceLimits, opts);
      return this.parseMarketStatus(fixed, removePriceLimits, opts);
    },
  );

  adaptTransaction = adapter<RawDict, RawDict, [opts?: RawDict]>(function (
    this: AbstractAdapter,
    raw,
    opts = {},
  ) {
    const fixed = this.fixTransaction(raw, opts);
    return this.parseTransaction(fixed, opts);
  });

  adaptDepositAddress = adapter<RawDict, RawDict, [opts?: RawDict]>(function (
    this: AbstractAdapter,
    raw,
    opts = {},
  ) {
    const fixed = this.fixDepositAddress(raw, opts);
    return this.parseDepositAddress(fixed, opts);
  });

  // ---- helpers ----

  getUniformizedTimestamp(timestamp: number | null | undefined): number | null {
    if (timestamp === null || timestamp === undefined) return null;
    if (timestamp > FUTURE_TIMESTAMP_THRESHOLD) {
      return timestamp / MSECONDS_TO_SECONDS;
    }
    return timestamp;
  }

  safeDecimal(container: RawDict, key: string, defaultValue: Decimal): Decimal {
    const val = container[key];
    if (val !== null && val !== undefined) {
      return toDecimal(val as string);
    }
    return defaultValue;
  }

  // ---- fix_* / parse_* hooks: subclasses override parse_*; fix_* default no-op ----

  fixOrder(raw: RawDict, _opts: RawDict = {}): RawDict {
    if (ExchangeConstantsOrderColumns.ID in raw) {
      raw[ExchangeConstantsOrderColumns.EXCHANGE_ID] = raw[ExchangeConstantsOrderColumns.ID];
      delete raw[ExchangeConstantsOrderColumns.ID];
    }
    return raw;
  }
  parseOrder(_fixed: RawDict, _opts: RawDict = {}): RawDict {
    throw new Error("parseOrder is not implemented");
  }

  fixOhlcv(raw: RawDict, _opts: RawDict = {}): RawDict {
    return raw;
  }
  parseOhlcv(_fixed: RawDict, _opts: RawDict = {}): RawDict[] {
    throw new Error("parseOhlcv is not implemented");
  }

  fixKline(raw: RawDict, _opts: RawDict = {}): RawDict {
    return raw;
  }
  parseKline(_fixed: RawDict, _opts: RawDict = {}): RawDict {
    throw new Error("parseKline is not implemented");
  }

  fixTicker(raw: RawDict, _opts: RawDict = {}): RawDict {
    return raw;
  }
  parseTicker(_fixed: RawDict, _opts: RawDict = {}): RawDict {
    throw new Error("parseTicker is not implemented");
  }

  createTickerFromKline(_kline: RawDict, _symbol: string, _opts: RawDict = {}): RawDict {
    throw new Error("createTickerFromKline is not implemented");
  }

  fixBalance(raw: RawDict, _opts: RawDict = {}): RawDict {
    return raw;
  }
  parseBalance(_fixed: RawDict, _opts: RawDict = {}): RawDict {
    throw new Error("parseBalance is not implemented");
  }

  fixOrderBook(raw: RawDict, _opts: RawDict = {}): RawDict {
    return raw;
  }
  parseOrderBook(_fixed: RawDict, _opts: RawDict = {}): RawDict {
    throw new Error("parseOrderBook is not implemented");
  }

  fixPublicRecentTrades(raw: RawDict[], _opts: RawDict = {}): RawDict[] {
    return raw;
  }
  parsePublicRecentTrades(_fixed: RawDict[], _opts: RawDict = {}): RawDict[] {
    throw new Error("parsePublicRecentTrades is not implemented");
  }

  fixTrades(raw: RawDict[], _opts: RawDict = {}): RawDict[] {
    for (const trade of raw) {
      trade[ExchangeConstantsOrderColumns.EXCHANGE_TRADE_ID] = trade[ExchangeConstantsOrderColumns.ID];
      delete trade[ExchangeConstantsOrderColumns.ID];
    }
    return raw;
  }
  parseTrades(_fixed: RawDict[], _opts: RawDict = {}): RawDict[] {
    throw new Error("parseTrades is not implemented");
  }

  fixPosition(raw: RawDict, _opts: RawDict = {}): RawDict {
    return raw;
  }
  parsePosition(_fixed: RawDict, _opts: RawDict = {}): RawDict {
    throw new Error("parsePosition is not implemented");
  }

  fixFundingRate(raw: RawDict, _opts: RawDict = {}): RawDict {
    return raw;
  }
  parseFundingRate(_fixed: RawDict, _opts: RawDict = {}): RawDict {
    throw new Error("parseFundingRate is not implemented");
  }

  fixLeverage(raw: RawDict, _opts: RawDict = {}): RawDict {
    return raw;
  }
  parseLeverage(_fixed: RawDict, _opts: RawDict = {}): RawDict {
    throw new Error("parseLeverage is not implemented");
  }

  fixFundingRateHistory(raw: RawDict[], _opts: RawDict = {}): RawDict[] {
    return raw;
  }
  parseFundingRateHistory(_fixed: RawDict[], _opts: RawDict = {}): RawDict[] {
    throw new Error("parseFundingRateHistory is not implemented");
  }

  fixLeverageTiers(raw: RawDict, _opts: RawDict = {}): RawDict {
    return raw;
  }
  parseLeverageTiers(_fixed: RawDict, _opts: RawDict = {}): Record<string, RawDict[]> {
    throw new Error("parseLeverageTiers is not implemented");
  }

  fixMarkPrice(raw: RawDict, _opts: RawDict = {}): RawDict {
    return raw;
  }
  parseMarkPrice(_fixed: RawDict, _opts: RawDict = {}): RawDict {
    throw new Error("parseMarkPrice is not implemented");
  }

  fixMarketStatus(raw: RawDict, _removePriceLimits = false, _opts: RawDict = {}): RawDict {
    return raw;
  }
  parseMarketStatus(_fixed: RawDict, _removePriceLimits = false, _opts: RawDict = {}): RawDict {
    throw new Error("parseMarketStatus is not implemented");
  }

  fixTransaction(raw: RawDict, _opts: RawDict = {}): RawDict {
    return raw;
  }
  parseTransaction(_fixed: RawDict, _opts: RawDict = {}): RawDict {
    throw new Error("parseTransaction is not implemented");
  }

  fixDepositAddress(raw: RawDict, _opts: RawDict = {}): RawDict {
    return raw;
  }
  parseDepositAddress(_fixed: RawDict, _opts: RawDict = {}): RawDict {
    throw new Error("parseDepositAddress is not implemented");
  }
}
