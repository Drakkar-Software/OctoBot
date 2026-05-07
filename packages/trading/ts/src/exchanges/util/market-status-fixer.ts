// Mirrors octobot_trading/exchanges/util/exchange_market_status_fixer.py
import type { OctoBotMarketStatus } from "../../types/index.js"

export function isMsValid(value: unknown, zeroValid = false): boolean {
  if (value === null || value === undefined) return false
  const n = typeof value === "string" ? parseFloat(value) : Number(value)
  if (Number.isNaN(n)) return false
  return zeroValid ? n >= 0 : n > 0
}

function tryParseFloat(val: unknown): number | null {
  if (val === null || val === undefined) return null
  if (typeof val === "number") return val
  if (typeof val === "string") {
    const n = parseFloat(val)
    return Number.isNaN(n) ? null : n
  }
  return null
}

export class ExchangeMarketStatusFixer {
  static readonly LIMIT_PRICE_MULTIPLIER = 1000
  static readonly LIMIT_AMOUNT_MAX_SUP_ATTENUATION = 8
  static readonly LIMIT_AMOUNT_MAX_MINUS_3_ATTENUATION = 8
  static readonly LIMIT_AMOUNT_MIN_ATTENUATION = 3
  static readonly LIMIT_AMOUNT_MIN_SUP_ATTENUATION = 1

  readonly marketStatus: OctoBotMarketStatus

  constructor(
    marketStatus: OctoBotMarketStatus,
    private readonly priceExample?: number,
  ) {
    // deep-clone to avoid mutating caller's object
    this.marketStatus = JSON.parse(JSON.stringify(marketStatus)) as OctoBotMarketStatus
    this._fixTyping()
    this._fixMarketStatusPrecision()
    this._fixMarketStatusLimits()
  }

  private _fixTyping(): void {
    const ms = this.marketStatus
    // precision.price / precision.amount → float
    if (ms.precision) {
      if (ms.precision.price !== null && ms.precision.price !== undefined) {
        const n = tryParseFloat(ms.precision.price)
        if (n !== null) ms.precision.price = n
      }
      if (ms.precision.amount !== null && ms.precision.amount !== undefined) {
        const n = tryParseFloat(ms.precision.amount)
        if (n !== null) ms.precision.amount = n
      }
    }
    // limits.cost.*
    if (ms.limits?.cost) {
      const c = ms.limits.cost
      const mn = tryParseFloat(c.min)
      if (mn !== null) c.min = mn
      const mx = tryParseFloat(c.max)
      if (mx !== null) c.max = mx
    }
    // limits.amount.*
    if (ms.limits?.amount) {
      const a = ms.limits.amount
      const mn = tryParseFloat(a.min)
      if (mn !== null) a.min = mn
      const mx = tryParseFloat(a.max)
      if (mx !== null) a.max = mx
    }
    // limits.price.*
    if (ms.limits?.price) {
      const p = ms.limits.price
      const mn = tryParseFloat(p.min)
      if (mn !== null) p.min = mn
      const mx = tryParseFloat(p.max)
      if (mx !== null) p.max = mx
    }
  }

  private _fixMarketStatusPrecision(): void {
    const ms = this.marketStatus
    if (!ms.precision) {
      ms.precision = { price: null, amount: null }
    }
    const hasValidAmount = isMsValid(ms.precision.amount, true)
    const hasValidPrice = isMsValid(ms.precision.price, true)
    if (!hasValidAmount || !hasValidPrice) {
      if (this.priceExample != null && this.priceExample > 0) {
        const precision = this._getPricePrecision()
        if (!hasValidAmount) ms.precision.amount = precision
        if (!hasValidPrice) ms.precision.price = precision
      }
    }
  }

  private _getPricePrecision(): number {
    if (this.priceExample == null) return 8
    const str = this.priceExample.toString()
    const dotIdx = str.indexOf(".")
    return dotIdx === -1 ? 0 : str.length - dotIdx - 1
  }

  private _fixMarketStatusLimits(): void {
    const ms = this.marketStatus
    if (!ms.limits) {
      ms.limits = {
        cost: { min: null, max: null },
        amount: { min: null, max: null },
        price: { min: null, max: null },
      }
    }
    const limits = ms.limits
    if (!limits.cost) limits.cost = { min: null, max: null }
    if (!limits.amount) limits.amount = { min: null, max: null }
    if (!limits.price) limits.price = { min: null, max: null }

    const allValid =
      isMsValid(limits.amount.min) &&
      isMsValid(limits.amount.max) &&
      isMsValid(limits.price.min) &&
      isMsValid(limits.price.max) &&
      isMsValid(limits.cost.min, true) &&
      isMsValid(limits.cost.max)

    if (!allValid) {
      this._fixMarketStatusLimitsFromCurrentData(limits)
      if (this.priceExample != null && !this._checkAllLimitsValid(limits)) {
        this._fixMarketStatusLimitsWithPrice(limits)
      }
    }
  }

  private _fixMarketStatusLimitsFromCurrentData(limits: OctoBotMarketStatus["limits"]): void {
    // compute missing cost from amount * price
    if (!isMsValid(limits.cost.max) && isMsValid(limits.amount.max) && isMsValid(limits.price.max)) {
      limits.cost.max = limits.amount.max! * limits.price.max!
    }
    if (!isMsValid(limits.cost.min) && isMsValid(limits.amount.min) && isMsValid(limits.price.min)) {
      limits.cost.min = limits.amount.min! * limits.price.min!
    }
    // compute missing amount from cost / price
    if (!isMsValid(limits.amount.max) && isMsValid(limits.cost.max) && isMsValid(limits.price.max) && limits.price.max! > 0) {
      limits.amount.max = limits.cost.max! / limits.price.max!
    }
    if (!isMsValid(limits.amount.min) && isMsValid(limits.cost.min) && isMsValid(limits.price.min) && limits.price.min! > 0) {
      limits.amount.min = limits.cost.min! / limits.price.min!
    }
    // set price to null if missing
    if (!isMsValid(limits.price.max)) limits.price.max = null
    if (!isMsValid(limits.price.min)) limits.price.min = null
    // ensure cost.min is 0 if still invalid
    if (!isMsValid(limits.cost.min, true)) limits.cost.min = 0
  }

  private _checkAllLimitsValid(limits: OctoBotMarketStatus["limits"]): boolean {
    return (
      isMsValid(limits.amount.min) &&
      isMsValid(limits.amount.max) &&
      isMsValid(limits.cost.min, true) &&
      isMsValid(limits.cost.max)
    )
  }

  private _fixMarketStatusLimitsWithPrice(limits: OctoBotMarketStatus["limits"]): void {
    if (this.priceExample == null || this.priceExample <= 0) return
    const price = this.priceExample
    const logPrice = Math.log10(price)

    let amountMin: number
    let amountMax: number
    if (logPrice >= 0) {
      amountMin = 10 ** (ExchangeMarketStatusFixer.LIMIT_AMOUNT_MIN_SUP_ATTENUATION - logPrice)
      amountMax = 10 ** (ExchangeMarketStatusFixer.LIMIT_AMOUNT_MAX_SUP_ATTENUATION - logPrice)
    } else {
      amountMin = 10 ** -(-logPrice + ExchangeMarketStatusFixer.LIMIT_AMOUNT_MIN_ATTENUATION)
      amountMax = 10 ** (-logPrice + ExchangeMarketStatusFixer.LIMIT_AMOUNT_MAX_MINUS_3_ATTENUATION)
    }

    if (!isMsValid(limits.amount.min, true)) limits.amount.min = amountMin
    if (!isMsValid(limits.amount.max)) limits.amount.max = amountMax

    const priceMin = isMsValid(limits.price.min, true)
      ? limits.price.min!
      : price / ExchangeMarketStatusFixer.LIMIT_PRICE_MULTIPLIER
    const priceMax = isMsValid(limits.price.max)
      ? limits.price.max!
      : price * ExchangeMarketStatusFixer.LIMIT_PRICE_MULTIPLIER

    limits.price.min = priceMin
    limits.price.max = priceMax

    // cost.min: prefer computed from exchange data, else 0
    if (!isMsValid(limits.cost.min, false)) {
      if (isMsValid(limits.price.min) && isMsValid(limits.amount.min)) {
        const candidate = limits.price.min! * limits.amount.min!
        limits.cost.min = isMsValid(candidate) ? candidate : 0
      } else {
        limits.cost.min = 0
      }
    }
    if (!isMsValid(limits.cost.max)) {
      limits.cost.max = priceMax * limits.amount.max!
    }
  }
}
