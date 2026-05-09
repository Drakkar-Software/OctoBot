import { describe, it, expect } from "vitest";
import {
  ExchangeMarketStatusFixer,
  isMsValid,
  checkMarketStatusValues,
  calculateAmounts,
  calculateCosts,
} from "../../src/exchanges/util/exchangeMarketStatusFixer.js";
import {
  ExchangeConstantsMarketStatusColumns as Ecmsc,
} from "../../src/exchanges/enums.js";

describe("isMsValid", () => {
  it("rejects null/undefined/empty/0", () => {
    expect(isMsValid(null)).toBe(false);
    expect(isMsValid(undefined)).toBe(false);
    expect(isMsValid("")).toBe(false);
    expect(isMsValid(0)).toBe(false);
  });
  it("accepts positive numbers and numeric strings", () => {
    expect(isMsValid(1)).toBe(true);
    expect(isMsValid("3.14")).toBe(true);
  });
  it("accepts 0 only when zeroValid", () => {
    expect(isMsValid(0, true)).toBe(true);
    expect(isMsValid(-1, true)).toBe(false);
  });
});

describe("checkMarketStatusValues", () => {
  it("returns true if all values pass", () => {
    expect(checkMarketStatusValues([1, 2, 3])).toBe(true);
  });
  it("returns false if any value fails", () => {
    expect(checkMarketStatusValues([1, null, 3])).toBe(false);
  });
});

describe("calculateAmounts/calculateCosts", () => {
  it("derives amount max from cost max / price max", () => {
    const limits = {
      [Ecmsc.LIMITS_COST]: { [Ecmsc.LIMITS_COST_MAX]: 1000, [Ecmsc.LIMITS_COST_MIN]: 10 },
      [Ecmsc.LIMITS_PRICE]: { [Ecmsc.LIMITS_PRICE_MAX]: 100, [Ecmsc.LIMITS_PRICE_MIN]: 1 },
      [Ecmsc.LIMITS_AMOUNT]: { [Ecmsc.LIMITS_AMOUNT_MAX]: null, [Ecmsc.LIMITS_AMOUNT_MIN]: null },
    };
    calculateAmounts(limits as any);
    expect(limits[Ecmsc.LIMITS_AMOUNT][Ecmsc.LIMITS_AMOUNT_MAX]).toBe(10);
    expect(limits[Ecmsc.LIMITS_AMOUNT][Ecmsc.LIMITS_AMOUNT_MIN]).toBe(10);
  });

  it("derives cost max from amount max * price max", () => {
    const limits = {
      [Ecmsc.LIMITS_COST]: { [Ecmsc.LIMITS_COST_MAX]: null, [Ecmsc.LIMITS_COST_MIN]: null },
      [Ecmsc.LIMITS_PRICE]: { [Ecmsc.LIMITS_PRICE_MAX]: 100, [Ecmsc.LIMITS_PRICE_MIN]: 1 },
      [Ecmsc.LIMITS_AMOUNT]: { [Ecmsc.LIMITS_AMOUNT_MAX]: 5, [Ecmsc.LIMITS_AMOUNT_MIN]: 1 },
    };
    calculateCosts(limits as any);
    expect(limits[Ecmsc.LIMITS_COST][Ecmsc.LIMITS_COST_MAX]).toBe(500);
    expect(limits[Ecmsc.LIMITS_COST][Ecmsc.LIMITS_COST_MIN]).toBe(1);
  });
});

describe("ExchangeMarketStatusFixer", () => {
  it("computes precision from a price example when missing", () => {
    const ms: any = {};
    new ExchangeMarketStatusFixer(ms, 0.000125);
    expect(ms[Ecmsc.PRECISION][Ecmsc.PRECISION_PRICE]).toBe(6);
    expect(ms[Ecmsc.PRECISION][Ecmsc.PRECISION_AMOUNT]).toBe(6);
  });

  it("fills limits from a price example when no specific data is given", () => {
    const ms: any = {};
    new ExchangeMarketStatusFixer(ms, 100);
    const limits = ms[Ecmsc.LIMITS];
    expect(limits[Ecmsc.LIMITS_PRICE][Ecmsc.LIMITS_PRICE_MAX]).toBeGreaterThan(100);
    expect(limits[Ecmsc.LIMITS_PRICE][Ecmsc.LIMITS_PRICE_MIN]).toBeLessThan(100);
    expect(limits[Ecmsc.LIMITS_AMOUNT][Ecmsc.LIMITS_AMOUNT_MIN]).toBeGreaterThan(0);
    expect(limits[Ecmsc.LIMITS_AMOUNT][Ecmsc.LIMITS_AMOUNT_MAX]).toBeGreaterThan(0);
  });

  it("converts string typed precision/limits to numbers", () => {
    const ms: any = {
      [Ecmsc.PRECISION]: { [Ecmsc.PRECISION_AMOUNT]: "0.0001", [Ecmsc.PRECISION_PRICE]: "0.01" },
      [Ecmsc.LIMITS]: {
        [Ecmsc.LIMITS_AMOUNT]: { [Ecmsc.LIMITS_AMOUNT_MIN]: "1", [Ecmsc.LIMITS_AMOUNT_MAX]: "100" },
        [Ecmsc.LIMITS_PRICE]: { [Ecmsc.LIMITS_PRICE_MIN]: "0.5", [Ecmsc.LIMITS_PRICE_MAX]: "5000" },
        [Ecmsc.LIMITS_COST]: { [Ecmsc.LIMITS_COST_MIN]: "0.5", [Ecmsc.LIMITS_COST_MAX]: "500000" },
      },
    };
    new ExchangeMarketStatusFixer(ms);
    expect(ms[Ecmsc.PRECISION][Ecmsc.PRECISION_AMOUNT]).toBe(0.0001);
    expect(ms[Ecmsc.LIMITS][Ecmsc.LIMITS_PRICE][Ecmsc.LIMITS_PRICE_MAX]).toBe(5000);
  });
});
