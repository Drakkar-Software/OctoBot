import { describe, expect, it } from "vitest"
import type { OctoBotMarketStatus } from "../../../src/types/index.js"
import { ExchangeMarketStatusFixer, isMsValid } from "../../../src/exchanges/util/market-status-fixer.js"

function makeMarket(overrides: Partial<OctoBotMarketStatus> = {}): OctoBotMarketStatus {
  return {
    symbol: "BTC/USDT",
    base: "BTC",
    quote: "USDT",
    active: true,
    type: "spot",
    precision: { price: 2, amount: 6 },
    limits: {
      amount: { min: 0.0001, max: 100 },
      price: { min: 100, max: 1_000_000 },
      cost: { min: 5, max: 100_000_000 },
    },
    ...overrides,
  }
}

describe("isMsValid", () => {
  it("returns false for null/undefined/NaN", () => {
    expect(isMsValid(null)).toBe(false)
    expect(isMsValid(undefined)).toBe(false)
    expect(isMsValid(Number.NaN)).toBe(false)
  })

  it("returns false for 0 when zeroValid=false (default)", () => {
    expect(isMsValid(0)).toBe(false)
  })

  it("returns true for 0 when zeroValid=true", () => {
    expect(isMsValid(0, true)).toBe(true)
  })

  it("returns true for positive numbers", () => {
    expect(isMsValid(1)).toBe(true)
    expect(isMsValid(0.001)).toBe(true)
  })

  it("parses valid numeric strings", () => {
    expect(isMsValid("0.001")).toBe(true)
    expect(isMsValid("invalid")).toBe(false)
  })
})

describe("ExchangeMarketStatusFixer – valid market (no changes needed)", () => {
  it("preserves a valid market status unchanged", () => {
    const ms = makeMarket()
    const fixer = new ExchangeMarketStatusFixer(ms, 30000)
    expect(fixer.marketStatus.limits.amount.min).toBe(0.0001)
    expect(fixer.marketStatus.limits.cost.min).toBe(5)
  })
})

describe("ExchangeMarketStatusFixer – missing limits", () => {
  it("computes missing amount.min from cost.min / price.min", () => {
    const ms = makeMarket({
      limits: {
        amount: { min: null, max: 100 },
        price: { min: 100, max: 1_000_000 },
        cost: { min: 5, max: 100_000_000 },
      },
    })
    const fixer = new ExchangeMarketStatusFixer(ms, 30000)
    // cost.min / price.min = 5 / 100 = 0.05
    expect(fixer.marketStatus.limits.amount.min).toBeCloseTo(0.05, 5)
  })

  it("computes missing cost.min from amount.min * price.min", () => {
    const ms = makeMarket({
      limits: {
        amount: { min: 0.001, max: 100 },
        price: { min: 200, max: 1_000_000 },
        cost: { min: null, max: 100_000_000 },
      },
    })
    const fixer = new ExchangeMarketStatusFixer(ms, 30000)
    // amount.min * price.min = 0.001 * 200 = 0.2
    expect(fixer.marketStatus.limits.cost.min).toBeCloseTo(0.2, 5)
  })

  it("sets cost.min to 0 when neither amount nor price available and no price example", () => {
    const ms = makeMarket({
      limits: {
        amount: { min: null, max: null },
        price: { min: null, max: null },
        cost: { min: null, max: null },
      },
    })
    const fixer = new ExchangeMarketStatusFixer(ms) // no price example
    expect(fixer.marketStatus.limits.cost.min).toBe(0)
  })
})

describe("ExchangeMarketStatusFixer – price example fallback", () => {
  it("calculates amount limits from price example when all limits are missing", () => {
    const ms = makeMarket({
      limits: {
        amount: { min: null, max: null },
        price: { min: null, max: null },
        cost: { min: null, max: null },
      },
    })
    const fixer = new ExchangeMarketStatusFixer(ms, 30000)
    expect(isMsValid(fixer.marketStatus.limits.amount.min)).toBe(true)
    expect(isMsValid(fixer.marketStatus.limits.amount.max)).toBe(true)
    expect(isMsValid(fixer.marketStatus.limits.price.min)).toBe(true)
    expect(isMsValid(fixer.marketStatus.limits.price.max)).toBe(true)
  })

  it("sets price limits based on LIMIT_PRICE_MULTIPLIER", () => {
    const ms = makeMarket({
      limits: {
        amount: { min: null, max: null },
        price: { min: null, max: null },
        cost: { min: null, max: null },
      },
    })
    const price = 30000
    const fixer = new ExchangeMarketStatusFixer(ms, price)
    expect(fixer.marketStatus.limits.price.min).toBeCloseTo(
      price / ExchangeMarketStatusFixer.LIMIT_PRICE_MULTIPLIER,
      5,
    )
    expect(fixer.marketStatus.limits.price.max).toBeCloseTo(
      price * ExchangeMarketStatusFixer.LIMIT_PRICE_MULTIPLIER,
      5,
    )
  })
})

describe("ExchangeMarketStatusFixer – precision fixing", () => {
  it("fixes precision from price example when missing", () => {
    const ms = makeMarket({ precision: { price: null, amount: null } })
    const fixer = new ExchangeMarketStatusFixer(ms, 30000.12)
    expect(fixer.marketStatus.precision.price).not.toBeNull()
    expect(fixer.marketStatus.precision.amount).not.toBeNull()
  })

  it("preserves valid precision", () => {
    const ms = makeMarket({ precision: { price: 4, amount: 8 } })
    const fixer = new ExchangeMarketStatusFixer(ms)
    expect(fixer.marketStatus.precision.price).toBe(4)
    expect(fixer.marketStatus.precision.amount).toBe(8)
  })

  it("converts string precision values to float", () => {
    const ms = makeMarket({
      precision: { price: "2" as unknown as number, amount: "6" as unknown as number },
    })
    const fixer = new ExchangeMarketStatusFixer(ms)
    expect(typeof fixer.marketStatus.precision.price).toBe("number")
    expect(fixer.marketStatus.precision.price).toBe(2)
  })
})

describe("ExchangeMarketStatusFixer – does not mutate input", () => {
  it("returns a deep copy — original unchanged", () => {
    const ms = makeMarket({
      limits: {
        amount: { min: null, max: null },
        price: { min: null, max: null },
        cost: { min: null, max: null },
      },
    })
    const originalAmountMin = ms.limits.amount.min
    new ExchangeMarketStatusFixer(ms, 30000)
    expect(ms.limits.amount.min).toBe(originalAmountMin)
  })
})
