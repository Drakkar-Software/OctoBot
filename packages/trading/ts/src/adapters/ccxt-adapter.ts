// Mirrors octobot_trading/exchanges/connectors/ccxt/ccxt_adapter.py
import type * as ccxt from "ccxt"

import {
  CcxtFundingColumns,
  CcxtOrderColumns,
  CcxtPositionColumns,
  FeeColumns,
  FundingColumns,
  LeverageTiersColumns,
  MarketStatusColumns,
  OrderColumns,
  PositionColumns,
  TickerColumns,
} from "../enums/exchange-constants.js"
import { MarginType, PositionMode } from "../enums/exchange-types.js"
import { PositionSide } from "../enums/position.js"
import { OrderStatus, TradeOrderType } from "../enums/order-status.js"
import { TimeFrameSeconds } from "../enums/timeframes.js"
import type {
  OctoBotBalance,
  OctoBotDepositAddress,
  OctoBotFundingRate,
  OctoBotLeverageTier,
  OctoBotMarketStatus,
  OctoBotOHLCV,
  OctoBotOrder,
  OctoBotOrderBook,
  OctoBotPosition,
  OctoBotTicker,
  OctoBotTrade,
  OctoBotTransaction,
} from "../types/index.js"
import { AbstractAdapter } from "./abstract-adapter.js"

export class CCXTAdapter extends AbstractAdapter {
  // ── fix_* overrides ───────────────────────────────────────────────────────

  override fixOrder(raw: Record<string, unknown>, opts?: Record<string, unknown>): Record<string, unknown> {
    const fixed = super.fixOrder(raw, opts)
    // Uniformize timestamp: ms → seconds
    if (typeof fixed[OrderColumns.TIMESTAMP] === "number") {
      fixed[OrderColumns.TIMESTAMP] = this.getUniformizedTimestamp(
        fixed[OrderColumns.TIMESTAMP] as number,
      )
    }
    // Register exchange fees
    this._registerExchangeFees(fixed)
    return fixed
  }

  override fixOhlcv(raw: ccxt.OHLCV[], opts?: Record<string, unknown>): ccxt.OHLCV[] {
    const timeFrame = (opts?.time_frame as string | undefined) ?? "1m"
    const candleSeconds = TimeFrameSeconds[timeFrame] ?? 60
    return raw
      .map((ohlcv, index) => {
        const tsCopy = [...ohlcv] as ccxt.OHLCV
        const ts = this.getUniformizedTimestamp(tsCopy[0])
        if (ts === null) {
          return null // will be filtered
        }
        // align to candle open boundary
        tsCopy[0] = ts - (ts % candleSeconds)
        // ensure numeric prices
        for (let i = 1; i <= 5; i++) {
          if (tsCopy[i] !== null && tsCopy[i] !== undefined) {
            tsCopy[i] = Number(tsCopy[i])
          }
        }
        return tsCopy
      })
      .filter((ohlcv, index, arr) => {
        if (ohlcv === null) {
          // Only remove if it's the last candle and DUMP_INCOMPLETE_LAST_CANDLE
          const connector = this.connector as { exchange?: { DUMP_INCOMPLETE_LAST_CANDLE?: boolean } }
          if (connector.exchange?.DUMP_INCOMPLETE_LAST_CANDLE && index === arr.length - 1) {
            return false
          }
          return false
        }
        return true
      }) as ccxt.OHLCV[]
  }

  override fixKline(raw: ccxt.OHLCV[], opts?: Record<string, unknown>): ccxt.OHLCV[] {
    return raw.map((kline) => {
      const copy = [...kline] as ccxt.OHLCV
      const ts = this.getUniformizedTimestamp(copy[0])
      copy[0] = ts !== null ? Math.floor(ts) : copy[0]
      for (let i = 1; i <= 5; i++) {
        if (copy[i] !== null && copy[i] !== undefined) copy[i] = Number(copy[i])
      }
      return copy
    })
  }

  override fixTicker(raw: ccxt.Ticker, _opts?: Record<string, unknown>): ccxt.Ticker {
    const fixed = { ...raw }
    if (fixed[TickerColumns.TIMESTAMP] !== null && fixed[TickerColumns.TIMESTAMP] !== undefined) {
      fixed[TickerColumns.TIMESTAMP] = Math.floor(
        this.getUniformizedTimestamp(fixed[TickerColumns.TIMESTAMP] as number) ?? 0,
      )
    }
    return fixed
  }

  override fixBalance(_raw: ccxt.Balances, _opts?: Record<string, unknown>): ccxt.Balances {
    return _raw
  }

  override fixOrderBook(raw: ccxt.OrderBook, _opts?: Record<string, unknown>): ccxt.OrderBook {
    const fixed = { ...raw }
    if (fixed.timestamp === null || fixed.timestamp === undefined) {
      // use current time (set externally after construction)
      fixed.timestamp = Math.floor(Date.now() / 1000)
    } else {
      fixed.timestamp = Math.floor(
        this.getUniformizedTimestamp(fixed.timestamp) ?? Date.now() / 1000,
      )
    }
    return fixed
  }

  override fixPublicRecentTrades(
    raw: ccxt.Trade[],
    _opts?: Record<string, unknown>,
  ): ccxt.Trade[] {
    return raw.map((trade) => {
      const t = { ...trade } as Record<string, unknown>
      if (typeof t[OrderColumns.TIMESTAMP] === "number") {
        t[OrderColumns.TIMESTAMP] = this.getUniformizedTimestamp(t[OrderColumns.TIMESTAMP] as number)
      }
      return t as unknown as ccxt.Trade
    })
  }

  override fixTrades(raw: ccxt.Trade[], _opts?: Record<string, unknown>): ccxt.Trade[] {
    return raw.map((trade) => {
      const t = { ...trade } as unknown as Record<string, unknown>
      // id → exchange_trade_id (base class handles id→exchange_trade_id)
      if (typeof t[OrderColumns.TIMESTAMP] === "number") {
        t[OrderColumns.TIMESTAMP] = this.getUniformizedTimestamp(t[OrderColumns.TIMESTAMP] as number)
      }
      // mirror: trade.exchange_id = trade.order (order id for this trade)
      t[OrderColumns.EXCHANGE_ID] = t[OrderColumns.ORDER]
      // set type if null: market for taker, limit for maker
      if (!t[OrderColumns.TYPE]) {
        t[OrderColumns.TYPE] =
          t[CcxtOrderColumns.TAKER_OR_MAKER] === "taker"
            ? TradeOrderType.MARKET
            : TradeOrderType.LIMIT
      }
      this._registerExchangeFees(t)
      return t as unknown as ccxt.Trade
    })
  }

  // ── parse_* implementations ───────────────────────────────────────────────

  parseOrder(fixed: Record<string, unknown>, _opts?: Record<string, unknown>): OctoBotOrder {
    return {
      exchange_id: String(fixed[OrderColumns.EXCHANGE_ID] ?? ""),
      timestamp: Number(fixed[OrderColumns.TIMESTAMP] ?? 0),
      symbol: String(fixed[OrderColumns.SYMBOL] ?? ""),
      type: String(fixed[OrderColumns.TYPE] ?? OrderStatus.UNKNOWN),
      side: fixed[OrderColumns.SIDE] as OctoBotOrder["side"],
      price: fixed[OrderColumns.PRICE] != null ? Number(fixed[OrderColumns.PRICE]) : null,
      amount: Number(fixed[OrderColumns.AMOUNT] ?? 0),
      filled: Number(fixed[OrderColumns.FILLED] ?? 0),
      remaining: Number(fixed[OrderColumns.REMAINING] ?? 0),
      cost: fixed[OrderColumns.COST] != null ? Number(fixed[OrderColumns.COST]) : null,
      average: fixed[OrderColumns.AVERAGE] != null ? Number(fixed[OrderColumns.AVERAGE]) : null,
      status: String(fixed[OrderColumns.STATUS] ?? OrderStatus.UNKNOWN),
      fee: this._parseFee(fixed[OrderColumns.FEE] as Record<string, unknown> | null | undefined),
      reduceOnly: Boolean(fixed[OrderColumns.REDUCE_ONLY] ?? false),
      stopPrice:
        fixed[OrderColumns.STOP_PRICE] != null ? Number(fixed[OrderColumns.STOP_PRICE]) : null,
      stopLossPrice:
        fixed[OrderColumns.STOP_LOSS_PRICE] != null
          ? Number(fixed[OrderColumns.STOP_LOSS_PRICE])
          : null,
      takeProfitPrice:
        fixed[OrderColumns.TAKE_PROFIT_PRICE] != null
          ? Number(fixed[OrderColumns.TAKE_PROFIT_PRICE])
          : null,
      triggerAbove:
        fixed[OrderColumns.TRIGGER_ABOVE] != null
          ? Boolean(fixed[OrderColumns.TRIGGER_ABOVE])
          : null,
      info: fixed[OrderColumns.INFO] as Record<string, unknown> | undefined,
    }
  }

  parseOhlcv(fixed: ccxt.OHLCV[], _opts?: Record<string, unknown>): OctoBotOHLCV[] {
    return fixed as OctoBotOHLCV[]
  }

  parseKline(fixed: ccxt.OHLCV[], _opts?: Record<string, unknown>): OctoBotOHLCV[] {
    return fixed as OctoBotOHLCV[]
  }

  parseTicker(fixed: ccxt.Ticker, _opts?: Record<string, unknown>): OctoBotTicker {
    const n = (v: ccxt.Num): number | null => (v == null || v === undefined ? null : Number(v))
    return {
      symbol: fixed.symbol,
      timestamp: fixed.timestamp != null ? Math.floor(fixed.timestamp) : null,
      datetime: fixed.datetime,
      high: n(fixed.high),
      low: n(fixed.low),
      bid: n(fixed.bid),
      bidVolume: n(fixed.bidVolume),
      ask: n(fixed.ask),
      askVolume: n(fixed.askVolume),
      vwap: n(fixed.vwap),
      open: n(fixed.open),
      close: n(fixed.close),
      last: n(fixed.last),
      previousClose: n(fixed.previousClose),
      change: n(fixed.change),
      percentage: n(fixed.percentage),
      average: n(fixed.average),
      baseVolume: n(fixed.baseVolume),
      quoteVolume: n(fixed.quoteVolume),
      info: fixed.info,
    }
  }

  parseBalance(fixed: ccxt.Balances, _opts?: Record<string, unknown>): OctoBotBalance {
    const result: OctoBotBalance = {}
    // Strip aggregate keys — mirrors CCXTAdapter.parse_balance
    const STRIP_KEYS = new Set(["free", "used", "total", "info", "datetime", "timestamp"])
    for (const [currency, data] of Object.entries(fixed)) {
      if (STRIP_KEYS.has(currency)) continue
      if (!data || typeof data !== "object") continue
      const d = data as ccxt.Balance
      result[currency] = {
        free: Number(d.free ?? 0),
        used: Number(d.used ?? 0),
        total: Number(d.total ?? 0),
      }
    }
    return result
  }

  parseOrderBook(fixed: ccxt.OrderBook, _opts?: Record<string, unknown>): OctoBotOrderBook {
    return {
      bids: (fixed.bids ?? []) as [number, number][],
      asks: (fixed.asks ?? []) as [number, number][],
      timestamp: fixed.timestamp != null ? Math.floor(fixed.timestamp) : null,
      datetime: fixed.datetime,
      nonce: fixed.nonce,
    }
  }

  parsePublicRecentTrades(
    fixed: ccxt.Trade[],
    _opts?: Record<string, unknown>,
  ): OctoBotTrade[] {
    return fixed.map((trade) => {
      const t = { ...trade } as unknown as Record<string, unknown>
      // remove fields not needed for public trades — mirrors parse_public_recent_trades
      delete t[OrderColumns.INFO]
      delete t[OrderColumns.DATETIME]
      delete t[OrderColumns.EXCHANGE_ID]
      delete t[OrderColumns.ORDER]
      delete t["fee"]
      delete t[OrderColumns.TYPE]
      delete t[CcxtOrderColumns.TAKER_OR_MAKER]
      return t as unknown as OctoBotTrade
    })
  }

  parseTrades(fixed: ccxt.Trade[], _opts?: Record<string, unknown>): OctoBotTrade[] {
    return fixed.map((trade) => {
      const t = { ...trade } as unknown as Record<string, unknown>
      return {
        exchange_id: String(t[OrderColumns.EXCHANGE_ID] ?? ""),
        exchange_trade_id: t["exchange_trade_id"] != null
          ? String(t["exchange_trade_id"])
          : null,
        order_id: t[OrderColumns.ORDER] != null ? String(t[OrderColumns.ORDER]) : null,
        timestamp: Number(t[OrderColumns.TIMESTAMP] ?? 0),
        symbol: String(t[OrderColumns.SYMBOL] ?? ""),
        type: String(t[OrderColumns.TYPE] ?? ""),
        side: t[OrderColumns.SIDE] as OctoBotTrade["side"],
        price: t[OrderColumns.PRICE] != null ? Number(t[OrderColumns.PRICE]) : null,
        amount: Number(t[OrderColumns.AMOUNT] ?? 0),
        filled: Number(t[OrderColumns.FILLED] ?? t[OrderColumns.AMOUNT] ?? 0),
        remaining: 0,
        cost: t[OrderColumns.COST] != null ? Number(t[OrderColumns.COST]) : null,
        average: null,
        status: "filled",
        fee: this._parseFee(t[OrderColumns.FEE] as Record<string, unknown> | null | undefined),
        reduceOnly: false,
        stopPrice: null,
        stopLossPrice: null,
        takeProfitPrice: null,
        triggerAbove: null,
        takerOrMaker: t[CcxtOrderColumns.TAKER_OR_MAKER] as "taker" | "maker" | null,
      }
    })
  }

  parsePosition(fixed: ccxt.Position, opts?: Record<string, unknown>): OctoBotPosition {
    const f = fixed as unknown as Record<string, unknown>
    const contracts = Number(f[CcxtPositionColumns.CONTRACTS] ?? 0) || 0
    const contractSize = Number(f[CcxtPositionColumns.CONTRACT_SIZE] ?? 1) || 1
    const isHedged = Boolean(f[CcxtPositionColumns.HEDGED] ?? false)
    const side = f[CcxtPositionColumns.SIDE] as string | undefined
    const positionMode = isHedged ? PositionMode.HEDGE : PositionMode.ONE_WAY
    const positionSide =
      positionMode === PositionMode.HEDGE
        ? side === PositionSide.LONG
          ? PositionSide.LONG
          : PositionSide.SHORT
        : PositionSide.BOTH
    const rawMarginType =
      (f[CcxtPositionColumns.MARGIN_TYPE] as string | undefined) ??
      (f[CcxtPositionColumns.MARGIN_MODE] as string | undefined)
    const marginType = rawMarginType
      ? ((rawMarginType.toLowerCase().includes("isolated")
          ? MarginType.ISOLATED
          : MarginType.CROSS) as OctoBotPosition["margin_type"])
      : null
    const liquidationPrice = Number(f[CcxtPositionColumns.LIQUIDATION_PRICE] ?? 0) || 0
    const size = side === PositionSide.LONG ? contracts * contractSize : -(contracts * contractSize)
    const isEmpty = contracts === 0

    return {
      symbol: String(f[CcxtPositionColumns.SYMBOL] ?? ""),
      timestamp:
        f[CcxtPositionColumns.TIMESTAMP] != null
          ? Math.floor(this.getUniformizedTimestamp(f[CcxtPositionColumns.TIMESTAMP] as number) ?? 0)
          : Math.floor(Date.now() / 1000),
      side: positionSide,
      margin_type: marginType,
      size,
      notional: isEmpty ? 0 : Number(f[CcxtPositionColumns.NOTIONAL] ?? 0) || 0,
      collateral: isEmpty ? 0 : Number(f[CcxtPositionColumns.COLLATERAL] ?? 0) || 0,
      initial_margin: isEmpty ? 0 : Number(f[CcxtPositionColumns.INITIAL_MARGIN] ?? 0) || 0,
      unrealised_pnl: isEmpty ? 0 : Number(f[CcxtPositionColumns.UNREALISED_PNL] ?? 0) || 0,
      realised_pnl: isEmpty ? 0 : Number(f[CcxtPositionColumns.REALISED_PNL] ?? 0) || 0,
      liquidation_price: liquidationPrice,
      mark_price: isEmpty ? 0 : Number(f[CcxtPositionColumns.MARK_PRICE] ?? 0) || 0,
      entry_price: isEmpty ? 0 : Number(f[CcxtPositionColumns.ENTRY_PRICE] ?? 0) || 0,
      leverage: Number(f[CcxtPositionColumns.LEVERAGE] ?? 1) || 1,
      position_mode: positionMode,
      auto_deposit_margin: false,
    }
  }

  parseFundingRate(fixed: ccxt.FundingRate, _opts?: Record<string, unknown>): OctoBotFundingRate {
    const f = fixed as unknown as Record<string, unknown>
    return {
      symbol: String(f[PositionColumns.SYMBOL] ?? ""),
      funding_rate: Number(f[CcxtFundingColumns.FUNDING_RATE] ?? 0),
      last_funding_time: Math.floor(
        this.getUniformizedTimestamp(
          Number(f[CcxtFundingColumns.PREVIOUS_FUNDING_TIMESTAMP] ?? 0),
        ) ?? 0,
      ),
      next_funding_time: Math.floor(
        this.getUniformizedTimestamp(
          Number(f[CcxtFundingColumns.FUNDING_TIMESTAMP] ?? 0),
        ) ?? 0,
      ),
      predicted_funding_rate: Number(f[CcxtFundingColumns.FUNDING_RATE] ?? 0),
    }
  }

  parseLeverageTiers(
    fixed: ccxt.LeverageTiers,
    _opts?: Record<string, unknown>,
  ): Record<string, OctoBotLeverageTier[]> {
    const result: Record<string, OctoBotLeverageTier[]> = {}
    for (const [symbol, tiers] of Object.entries(fixed)) {
      result[symbol] = (tiers ?? []).map((tier, idx) => {
        const t = tier as unknown as Record<string, unknown>
        return {
          tier: Number(t[LeverageTiersColumns.TIER] ?? idx + 1),
          currency: String(t[LeverageTiersColumns.CURRENCY] ?? ""),
          min_notional: Number(t[LeverageTiersColumns.MIN_NOTIONAL] ?? 0),
          max_notional: Number(t[LeverageTiersColumns.MAX_NOTIONAL] ?? 0),
          maintenance_margin_rate: Number(t[LeverageTiersColumns.MAINTENANCE_MARGIN_RATE] ?? 0),
          max_leverage: Number(t[LeverageTiersColumns.MAX_LEVERAGE] ?? 1),
          info: t[LeverageTiersColumns.INFO] as Record<string, unknown> | undefined,
        }
      })
    }
    return result
  }

  parseMarketStatus(fixed: ccxt.Market, _opts?: Record<string, unknown>): OctoBotMarketStatus {
    const f = fixed as unknown as Record<string, unknown>
    const precision = (f[MarketStatusColumns.PRECISION] as Record<string, unknown> | undefined) ?? {}
    const limits = (f[MarketStatusColumns.LIMITS] as Record<string, unknown> | undefined) ?? {}
    const amountLimits = (limits[MarketStatusColumns.LIMITS_AMOUNT] as Record<string, unknown> | undefined) ?? {}
    const priceLimits = (limits[MarketStatusColumns.LIMITS_PRICE] as Record<string, unknown> | undefined) ?? {}
    const costLimits = (limits[MarketStatusColumns.LIMITS_COST] as Record<string, unknown> | undefined) ?? {}

    return {
      symbol: String(f[MarketStatusColumns.SYMBOL] ?? ""),
      id: f[MarketStatusColumns.ID] != null ? String(f[MarketStatusColumns.ID]) : undefined,
      base: String(f[MarketStatusColumns.CURRENCY] ?? ""),
      quote: String(f[MarketStatusColumns.MARKET] ?? ""),
      active: Boolean(f[MarketStatusColumns.ACTIVE] ?? false),
      type: String(f[MarketStatusColumns.TYPE] ?? "spot"),
      expiry: f[MarketStatusColumns.EXPIRY] != null
        ? String(f[MarketStatusColumns.EXPIRY])
        : null,
      precision: {
        price: precision[MarketStatusColumns.PRECISION_PRICE] != null
          ? Number(precision[MarketStatusColumns.PRECISION_PRICE])
          : null,
        amount: precision[MarketStatusColumns.PRECISION_AMOUNT] != null
          ? Number(precision[MarketStatusColumns.PRECISION_AMOUNT])
          : null,
      },
      limits: {
        amount: {
          min: amountLimits[MarketStatusColumns.LIMITS_AMOUNT_MIN] != null
            ? Number(amountLimits[MarketStatusColumns.LIMITS_AMOUNT_MIN])
            : null,
          max: amountLimits[MarketStatusColumns.LIMITS_AMOUNT_MAX] != null
            ? Number(amountLimits[MarketStatusColumns.LIMITS_AMOUNT_MAX])
            : null,
        },
        price: {
          min: priceLimits[MarketStatusColumns.LIMITS_PRICE_MIN] != null
            ? Number(priceLimits[MarketStatusColumns.LIMITS_PRICE_MIN])
            : null,
          max: priceLimits[MarketStatusColumns.LIMITS_PRICE_MAX] != null
            ? Number(priceLimits[MarketStatusColumns.LIMITS_PRICE_MAX])
            : null,
        },
        cost: {
          min: costLimits[MarketStatusColumns.LIMITS_COST_MIN] != null
            ? Number(costLimits[MarketStatusColumns.LIMITS_COST_MIN])
            : null,
          max: costLimits[MarketStatusColumns.LIMITS_COST_MAX] != null
            ? Number(costLimits[MarketStatusColumns.LIMITS_COST_MAX])
            : null,
        },
      },
      taker: f["taker"] != null ? Number(f["taker"]) : null,
      maker: f["maker"] != null ? Number(f["maker"]) : null,
      info: f[MarketStatusColumns.INFO] as Record<string, unknown> | undefined,
    }
  }

  parseTransaction(
    fixed: ccxt.Transaction,
    _opts?: Record<string, unknown>,
  ): OctoBotTransaction {
    const f = fixed as unknown as Record<string, unknown>
    return {
      id: String(f["id"] ?? ""),
      txid: f["txid"] != null ? String(f["txid"]) : null,
      timestamp:
        f["timestamp"] != null
          ? Math.floor(this.getUniformizedTimestamp(Number(f["timestamp"])) ?? 0)
          : null,
      address_from: f["addressFrom"] != null ? String(f["addressFrom"]) : null,
      address_to: f["address"] != null ? String(f["address"]) : null,
      tag: f["tag"] != null ? String(f["tag"]) : null,
      type: String(f["type"] ?? ""),
      amount: Number(f["amount"] ?? 0),
      currency: String(f["currency"] ?? ""),
      status: String(f["status"] ?? ""),
      fee: f["fee"] != null ? Number((f["fee"] as Record<string, unknown>)?.["cost"] ?? 0) : null,
      network: f["network"] != null ? String(f["network"]) : null,
      info: f["info"] as Record<string, unknown> | undefined,
    }
  }

  parseDepositAddress(
    fixed: ccxt.DepositAddress,
    _opts?: Record<string, unknown>,
  ): OctoBotDepositAddress {
    const f = fixed as unknown as Record<string, unknown>
    return {
      currency: String(f["currency"] ?? ""),
      network: f["network"] != null ? String(f["network"]) : null,
      address: String(f["address"] ?? ""),
      tag: f["tag"] != null ? String(f["tag"]) : null,
      info: f["info"] as Record<string, unknown> | undefined,
    }
  }

  // ── private helpers ───────────────────────────────────────────────────────

  private _parseFee(
    fee: Record<string, unknown> | null | undefined,
  ): OctoBotOrder["fee"] {
    if (!fee) return null
    return {
      type: fee[FeeColumns.TYPE] != null ? String(fee[FeeColumns.TYPE]) : null,
      currency: fee[FeeColumns.CURRENCY] != null ? String(fee[FeeColumns.CURRENCY]) : null,
      rate: fee[FeeColumns.RATE] != null ? Number(fee[FeeColumns.RATE]) : null,
      cost: Number(fee[FeeColumns.COST] ?? 0),
      is_from_exchange: Boolean(fee[FeeColumns.IS_FROM_EXCHANGE] ?? false),
      exchange_original_cost:
        fee[FeeColumns.EXCHANGE_ORIGINAL_COST] != null
          ? Number(fee[FeeColumns.EXCHANGE_ORIGINAL_COST])
          : null,
    }
  }

  private _registerExchangeFees(orderOrTrade: Record<string, unknown>): void {
    const fee = orderOrTrade[OrderColumns.FEE] as Record<string, unknown> | null | undefined
    if (!fee) return
    fee[FeeColumns.EXCHANGE_ORIGINAL_COST] = fee[FeeColumns.COST]
    fee[FeeColumns.IS_FROM_EXCHANGE] = true
  }
}
