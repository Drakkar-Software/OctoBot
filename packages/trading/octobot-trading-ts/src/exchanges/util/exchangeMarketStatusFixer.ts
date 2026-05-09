import {
  ExchangeConstantsMarketStatusColumns as Ecmsc,
  ExchangeConstantsMarketStatusInfoColumns as Ecmsic,
} from "../enums.js";
import { Logger, getLogger } from "./logger.js";

export type MarketStatus = Record<string, any>;

export function isMsValid(value: unknown, zeroValid = false): boolean {
  let v: number;
  if (typeof value === "string") {
    const parsed = parseFloat(value);
    if (Number.isNaN(parsed)) return false;
    v = parsed;
  } else if (typeof value === "number") {
    v = value;
  } else {
    return false;
  }
  if (Number.isNaN(v)) return false;
  return zeroValid ? v >= 0 : v > 0;
}

export function checkMarketStatusValues(values: Iterable<unknown>, zeroValid = false): boolean {
  for (const v of values) {
    if (!isMsValid(v, zeroValid)) return false;
  }
  return true;
}

export function checkMarketStatusLimits(marketLimit: Record<string, Record<string, unknown>>): boolean {
  for (const key of Object.keys(marketLimit)) {
    if (!checkMarketStatusValues(Object.values(marketLimit[key]))) return false;
  }
  return true;
}

function getMarketsLimit(marketLimit: Record<string, Record<string, any>>) {
  return {
    limitCost: Ecmsc.LIMITS_COST in marketLimit ? marketLimit[Ecmsc.LIMITS_COST] : null,
    limitPrice: Ecmsc.LIMITS_PRICE in marketLimit ? marketLimit[Ecmsc.LIMITS_PRICE] : null,
    limitAmount: Ecmsc.LIMITS_AMOUNT in marketLimit ? marketLimit[Ecmsc.LIMITS_AMOUNT] : null,
  };
}

export function calculateAmounts(marketLimit: Record<string, Record<string, any>>): void {
  const { limitCost, limitPrice, limitAmount } = getMarketsLimit(marketLimit);
  if (!limitAmount || !limitCost || !limitPrice) return;

  if (
    !isMsValid(limitAmount[Ecmsc.LIMITS_AMOUNT_MAX]) &&
    Ecmsc.LIMITS_COST_MAX in limitCost &&
    Ecmsc.LIMITS_PRICE_MAX in limitPrice
  ) {
    if (
      isMsValid(limitCost[Ecmsc.LIMITS_COST_MAX]) &&
      isMsValid(limitPrice[Ecmsc.LIMITS_PRICE_MAX]) &&
      Number(limitPrice[Ecmsc.LIMITS_PRICE_MAX]) > 0
    ) {
      limitAmount[Ecmsc.LIMITS_AMOUNT_MAX] =
        Number(limitCost[Ecmsc.LIMITS_COST_MAX]) / Number(limitPrice[Ecmsc.LIMITS_PRICE_MAX]);
    }
  }

  if (
    !isMsValid(limitAmount[Ecmsc.LIMITS_AMOUNT_MIN]) &&
    Ecmsc.LIMITS_COST_MIN in limitCost &&
    Ecmsc.LIMITS_PRICE_MIN in limitPrice
  ) {
    if (
      isMsValid(limitCost[Ecmsc.LIMITS_COST_MIN]) &&
      isMsValid(limitPrice[Ecmsc.LIMITS_PRICE_MIN]) &&
      Number(limitPrice[Ecmsc.LIMITS_PRICE_MIN]) > 0
    ) {
      limitAmount[Ecmsc.LIMITS_AMOUNT_MIN] =
        Number(limitCost[Ecmsc.LIMITS_COST_MIN]) / Number(limitPrice[Ecmsc.LIMITS_PRICE_MIN]);
    }
  }
}

export function calculateCosts(marketLimit: Record<string, Record<string, any>>): void {
  const { limitCost, limitPrice, limitAmount } = getMarketsLimit(marketLimit);
  if (!limitAmount || !limitCost || !limitPrice) return;

  if (
    !isMsValid(limitCost[Ecmsc.LIMITS_COST_MAX]) &&
    Ecmsc.LIMITS_AMOUNT_MAX in limitAmount &&
    Ecmsc.LIMITS_PRICE_MAX in limitPrice
  ) {
    if (isMsValid(limitAmount[Ecmsc.LIMITS_AMOUNT_MAX]) && isMsValid(limitPrice[Ecmsc.LIMITS_PRICE_MAX])) {
      limitCost[Ecmsc.LIMITS_COST_MAX] =
        Number(limitAmount[Ecmsc.LIMITS_AMOUNT_MAX]) * Number(limitPrice[Ecmsc.LIMITS_PRICE_MAX]);
    }
  }

  if (
    !isMsValid(limitCost[Ecmsc.LIMITS_COST_MIN]) &&
    Ecmsc.LIMITS_AMOUNT_MIN in limitAmount &&
    Ecmsc.LIMITS_PRICE_MIN in limitPrice
  ) {
    if (isMsValid(limitAmount[Ecmsc.LIMITS_AMOUNT_MIN]) && isMsValid(limitPrice[Ecmsc.LIMITS_PRICE_MIN])) {
      limitCost[Ecmsc.LIMITS_COST_MIN] =
        Number(limitAmount[Ecmsc.LIMITS_AMOUNT_MIN]) * Number(limitPrice[Ecmsc.LIMITS_PRICE_MIN]);
    }
  }
}

export function updatePrices(marketLimit: Record<string, Record<string, any>>): void {
  const { limitPrice } = getMarketsLimit(marketLimit);
  if (!limitPrice) return;
  if (!isMsValid(limitPrice[Ecmsc.LIMITS_PRICE_MAX])) limitPrice[Ecmsc.LIMITS_PRICE_MAX] = null;
  if (!isMsValid(limitPrice[Ecmsc.LIMITS_PRICE_MIN])) limitPrice[Ecmsc.LIMITS_PRICE_MIN] = null;
}

export function fixMarketStatusLimitsFromCurrentData(marketLimit: Record<string, Record<string, any>>): void {
  if (!checkMarketStatusValues(Object.values(marketLimit[Ecmsc.LIMITS_COST] || {}))) {
    calculateCosts(marketLimit);
  }
  if (!checkMarketStatusValues(Object.values(marketLimit[Ecmsc.LIMITS_AMOUNT] || {}))) {
    calculateAmounts(marketLimit);
  }
  if (!checkMarketStatusValues(Object.values(marketLimit[Ecmsc.LIMITS_PRICE] || {}))) {
    updatePrices(marketLimit);
  }
  if (!isMsValid(marketLimit[Ecmsc.LIMITS_COST]?.[Ecmsc.LIMITS_COST_MIN])) {
    if (!marketLimit[Ecmsc.LIMITS_COST]) marketLimit[Ecmsc.LIMITS_COST] = {};
    marketLimit[Ecmsc.LIMITS_COST][Ecmsc.LIMITS_COST_MIN] = 0;
  }
}

export class ExchangeMarketStatusFixer {
  static readonly LIMIT_PRICE_MULTIPLIER = 1000;
  static readonly LIMIT_COST_MULTIPLIER = 1;

  static readonly LIMIT_AMOUNT_MAX_SUP_ATTENUATION = 8;
  static readonly LIMIT_AMOUNT_MAX_MINUS_3_ATTENUATION = 8;
  static readonly LIMIT_AMOUNT_MIN_ATTENUATION = 3;
  static readonly LIMIT_AMOUNT_MIN_SUP_ATTENUATION = 1;

  protected logger: Logger;
  marketStatus: MarketStatus;
  priceExample: number | null;
  marketStatusSpecific: Record<string, any> | null;

  constructor(marketStatus: MarketStatus, priceExample: number | null = null) {
    this.logger = getLogger(this.constructor.name);
    this.marketStatus = marketStatus;
    this.priceExample = priceExample;
    this.marketStatusSpecific = (Ecmsc.INFO in this.marketStatus)
      ? (this.marketStatus[Ecmsc.INFO] as Record<string, any>)
      : null;

    this.fixTyping();
    this.fixMarketStatusPrecision();
    this.fixMarketStatusLimits();
  }

  protected convertValuesToFloat(
    element: Record<string, any>,
    parentKeys: string[],
    keyWhitelist: string[],
  ): void {
    let cur: Record<string, any> | undefined = element;
    for (const k of parentKeys) {
      if (!cur || !(k in cur)) return;
      cur = cur[k] as Record<string, any>;
    }
    if (!cur) return;
    for (const [k, v] of Object.entries(cur)) {
      if (keyWhitelist.includes(k) && typeof v === "string") {
        const parsed = parseFloat(v);
        if (!Number.isNaN(parsed)) cur[k] = parsed;
        else this.logger.debug(`Impossible to convert ${v} to float in ${k} market status`);
      }
    }
  }

  protected fixTyping(): void {
    this.convertValuesToFloat(
      this.marketStatus,
      [Ecmsc.PRECISION],
      [Ecmsc.PRECISION_AMOUNT, Ecmsc.PRECISION_PRICE],
    );
    this.convertValuesToFloat(
      this.marketStatus,
      [Ecmsc.LIMITS, Ecmsc.LIMITS_COST],
      [Ecmsc.LIMITS_COST_MAX, Ecmsc.LIMITS_COST_MIN],
    );
    this.convertValuesToFloat(
      this.marketStatus,
      [Ecmsc.LIMITS, Ecmsc.LIMITS_AMOUNT],
      [Ecmsc.LIMITS_AMOUNT_MAX, Ecmsc.LIMITS_AMOUNT_MIN],
    );
    this.convertValuesToFloat(
      this.marketStatus,
      [Ecmsc.LIMITS, Ecmsc.LIMITS_PRICE],
      [Ecmsc.LIMITS_PRICE_MAX, Ecmsc.LIMITS_PRICE_MIN],
    );
  }

  protected fixMarketStatusPrecision(): void {
    if (!(Ecmsc.PRECISION in this.marketStatus)) {
      this.marketStatus[Ecmsc.PRECISION] = {
        [Ecmsc.PRECISION_AMOUNT]: null,
        [Ecmsc.PRECISION_PRICE]: null,
      };
    }
    const marketPrecision = this.marketStatus[Ecmsc.PRECISION];
    if (!checkMarketStatusValues(
      [marketPrecision[Ecmsc.PRECISION_AMOUNT], marketPrecision[Ecmsc.PRECISION_PRICE]],
      true,
    )) {
      if (this.priceExample !== null) {
        this.fixMarketStatusPrecisionWithPrice();
      } else if (this.marketStatusSpecific) {
        this.fixMarketStatusPrecisionWithSpecific();
      }
    }
  }

  protected fixMarketStatusLimits(): void {
    if (!(Ecmsc.LIMITS in this.marketStatus)) this.marketStatus[Ecmsc.LIMITS] = {};
    const marketLimit = this.marketStatus[Ecmsc.LIMITS];
    if (!(Ecmsc.LIMITS_COST in marketLimit)) {
      marketLimit[Ecmsc.LIMITS_COST] = { [Ecmsc.LIMITS_COST_MAX]: null, [Ecmsc.LIMITS_COST_MIN]: null };
    }
    if (!(Ecmsc.LIMITS_AMOUNT in marketLimit)) {
      marketLimit[Ecmsc.LIMITS_AMOUNT] = { [Ecmsc.LIMITS_AMOUNT_MAX]: null, [Ecmsc.LIMITS_AMOUNT_MIN]: null };
    }
    if (!(Ecmsc.LIMITS_PRICE in marketLimit)) {
      marketLimit[Ecmsc.LIMITS_PRICE] = { [Ecmsc.LIMITS_PRICE_MAX]: null, [Ecmsc.LIMITS_PRICE_MIN]: null };
    }
    if (!checkMarketStatusLimits(marketLimit)) {
      fixMarketStatusLimitsFromCurrentData(marketLimit);
      if (this.marketStatusSpecific && !checkMarketStatusLimits(marketLimit)) {
        this.fixMarketStatusLimitsWithSpecific();
      }
      if (this.priceExample !== null && !checkMarketStatusLimits(marketLimit)) {
        this.fixMarketStatusLimitsWithPrice();
      }
    }
  }

  protected calculateAmount(): { amountMin: number; amountMax: number } {
    const px = this.priceExample as number;
    const amountLogPrice = Math.log10(px);
    if (amountLogPrice >= 0) {
      return {
        amountMin: 10 ** (ExchangeMarketStatusFixer.LIMIT_AMOUNT_MIN_SUP_ATTENUATION - amountLogPrice),
        amountMax: 10 ** (ExchangeMarketStatusFixer.LIMIT_AMOUNT_MAX_SUP_ATTENUATION - amountLogPrice),
      };
    }
    return {
      amountMin: 10 ** -(amountLogPrice + ExchangeMarketStatusFixer.LIMIT_AMOUNT_MIN_ATTENUATION),
      amountMax: 10 ** (-amountLogPrice + ExchangeMarketStatusFixer.LIMIT_AMOUNT_MAX_MINUS_3_ATTENUATION),
    };
  }

  protected fixMarketStatusLimitsWithPrice(): void {
    const px = this.priceExample as number;
    const { amountMin: candidateAmountMin, amountMax: candidateAmountMax } = this.calculateAmount();
    const limitsAmount = this.marketStatus[Ecmsc.LIMITS][Ecmsc.LIMITS_AMOUNT];
    let amountMin = limitsAmount[Ecmsc.LIMITS_AMOUNT_MIN];
    if (!isMsValid(amountMin, true)) amountMin = candidateAmountMin;
    let amountMax = limitsAmount[Ecmsc.LIMITS_AMOUNT_MAX];
    if (!isMsValid(amountMax, false)) amountMax = candidateAmountMax;

    const limitsPrice = this.marketStatus[Ecmsc.LIMITS][Ecmsc.LIMITS_PRICE];
    let priceMin = limitsPrice[Ecmsc.LIMITS_PRICE_MIN];
    if (!isMsValid(priceMin, true)) priceMin = px / ExchangeMarketStatusFixer.LIMIT_PRICE_MULTIPLIER;
    let priceMax = limitsPrice[Ecmsc.LIMITS_PRICE_MAX];
    if (!isMsValid(priceMax, false)) priceMax = px * ExchangeMarketStatusFixer.LIMIT_PRICE_MULTIPLIER;

    const limitCost = this.marketStatus[Ecmsc.LIMITS][Ecmsc.LIMITS_COST] || {};
    let costMin = limitCost[Ecmsc.LIMITS_COST_MIN];
    if (!isMsValid(costMin, false)) {
      let updatedCost = false;
      if (
        isMsValid(limitsPrice[Ecmsc.LIMITS_PRICE_MIN]) &&
        isMsValid(limitsAmount[Ecmsc.LIMITS_AMOUNT_MIN])
      ) {
        const candidateCostMin = Number(limitsPrice[Ecmsc.LIMITS_PRICE_MIN]) * Number(limitsAmount[Ecmsc.LIMITS_AMOUNT_MIN]);
        if (isMsValid(candidateCostMin, false)) {
          costMin = candidateCostMin;
          updatedCost = true;
        }
      }
      if (!updatedCost) costMin = 0;
    }
    let costMax = limitCost[Ecmsc.LIMITS_COST_MAX];
    if (!isMsValid(costMax, false)) costMax = priceMax * amountMax;

    this.marketStatus[Ecmsc.LIMITS] = {
      [Ecmsc.LIMITS_AMOUNT]: { [Ecmsc.LIMITS_AMOUNT_MIN]: amountMin, [Ecmsc.LIMITS_AMOUNT_MAX]: amountMax },
      [Ecmsc.LIMITS_PRICE]: { [Ecmsc.LIMITS_PRICE_MIN]: priceMin, [Ecmsc.LIMITS_PRICE_MAX]: priceMax },
      [Ecmsc.LIMITS_COST]: { [Ecmsc.LIMITS_COST_MIN]: costMin, [Ecmsc.LIMITS_COST_MAX]: costMax },
    };
  }

  protected getPricePrecision(): number {
    const s = String(this.priceExample);
    if (!s.includes(".")) return 0;
    return s.split(".")[1].length;
  }

  protected fixMarketStatusPrecisionWithPrice(): void {
    const precision = this.getPricePrecision();
    const p = this.marketStatus[Ecmsc.PRECISION];
    if (!isMsValid(p[Ecmsc.PRECISION_AMOUNT], true)) p[Ecmsc.PRECISION_AMOUNT] = precision;
    if (!isMsValid(p[Ecmsc.PRECISION_PRICE], true)) p[Ecmsc.PRECISION_PRICE] = precision;
  }

  protected fixMarketStatusPrecisionWithSpecific(): void {
    // binance specific — no-op like Python.
  }

  protected fixMarketStatusLimitsWithSpecific(): void {
    const marketLimit = this.marketStatus[Ecmsc.LIMITS];
    try {
      if (this.marketStatusSpecific && Ecmsic.FILTERS in this.marketStatusSpecific) {
        const filters = this.marketStatusSpecific[Ecmsic.FILTERS] as Array<Record<string, any>>;
        for (const f of filters) {
          if (!(Ecmsic.FILTER_TYPE in f)) continue;
          if (f[Ecmsic.FILTER_TYPE] === Ecmsic.PRICE_FILTER) {
            const maxPrice = parseFloat(f[Ecmsic.MAX_PRICE]);
            if (
              isMsValid(maxPrice) &&
              !isMsValid(marketLimit[Ecmsc.LIMITS_PRICE][Ecmsc.LIMITS_PRICE_MAX])
            ) {
              marketLimit[Ecmsc.LIMITS_PRICE][Ecmsc.LIMITS_PRICE_MAX] = maxPrice;
            }
            const minPrice = parseFloat(f[Ecmsic.MIN_PRICE]);
            if (
              isMsValid(minPrice) &&
              !isMsValid(marketLimit[Ecmsc.LIMITS_PRICE][Ecmsc.LIMITS_PRICE_MIN])
            ) {
              marketLimit[Ecmsc.LIMITS_PRICE][Ecmsc.LIMITS_PRICE_MIN] = minPrice;
            }
          } else if (f[Ecmsic.FILTER_TYPE] === Ecmsic.LOT_SIZE) {
            const maxQty = parseFloat(f[Ecmsic.MAX_QTY]);
            if (
              isMsValid(maxQty) &&
              !isMsValid(marketLimit[Ecmsc.LIMITS_AMOUNT][Ecmsc.LIMITS_AMOUNT_MAX])
            ) {
              marketLimit[Ecmsc.LIMITS_AMOUNT][Ecmsc.LIMITS_AMOUNT_MAX] = maxQty;
            }
            const minQty = parseFloat(f[Ecmsic.MIN_QTY]);
            if (
              isMsValid(minQty) &&
              !isMsValid(marketLimit[Ecmsc.LIMITS_AMOUNT][Ecmsc.LIMITS_AMOUNT_MIN])
            ) {
              marketLimit[Ecmsc.LIMITS_AMOUNT][Ecmsc.LIMITS_AMOUNT_MIN] = minQty;
            }
          }
        }
        calculateCosts(marketLimit);
      }
    } catch {
      // mirror Python's broad-catch silence
    }
  }
}
