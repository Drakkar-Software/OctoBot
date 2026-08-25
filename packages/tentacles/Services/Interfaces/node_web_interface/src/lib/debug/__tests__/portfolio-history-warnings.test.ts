import { describe, expect, it } from "vitest"

import type { Account } from "@/client"
import {
  formatSuggestedTradePair,
  getNegativeHoldingsWarnings,
} from "@/lib/debug/portfolio-history-warnings"
import type { PortfolioHistoricalValuesState } from "@/lib/debug/portfolio-historical-values-types"

type AssetInput = {
  holdings: number
  value?: number
}

type DayInput = {
  timestamp?: string
  total?: number
  assets: Record<string, AssetInput | number>
}

function makeHistoryState(days: DayInput[]): PortfolioHistoricalValuesState {
  return {
    version: "1.0.0",
    history: {
      unit: "USDT",
      values: days.map((day, dayIndex) => {
        const assetEntries = Object.entries(day.assets).map(([symbol, assetInput]) => {
          const holdings = typeof assetInput === "number" ? assetInput : assetInput.holdings
          const value =
            typeof assetInput === "number" ? assetInput : (assetInput.value ?? assetInput.holdings)
          return { symbol, holdings, value }
        })
        const defaultTotal = assetEntries.reduce(
          (runningTotal, asset) => runningTotal + Math.abs(asset.value),
          0,
        )
        return {
          timestamp: day.timestamp ?? `2024-01-0${dayIndex + 1}T00:00:00Z`,
          total: day.total ?? defaultTotal,
          assets: [
            {
              trading_type: "spot",
              assets: assetEntries,
            },
          ],
        }
      }),
    },
  }
}

describe("formatSuggestedTradePair", () => {
  it("puts the acquired asset first when quote went negative", () => {
    expect(formatSuggestedTradePair("USDT", "SOL", "USDT")).toBe("SOL/USDT")
  })

  it("puts the sold asset first when quote increased", () => {
    expect(formatSuggestedTradePair("ADA", "USDT", "USDT")).toBe("ADA/USDT")
  })

  it("puts the negative crypto first for crypto-crypto moves", () => {
    expect(formatSuggestedTradePair("ETH", "BTC", "USDT")).toBe("ETH/BTC")
  })
})

describe("getNegativeHoldingsWarnings", () => {
  it("returns deduplicated warnings for significant negative holdings", () => {
    const state = makeHistoryState([
      {
        total: 1000,
        assets: {
          ADA: { holdings: -10, value: -100 },
          BTC: { holdings: 2, value: 900 },
        },
      },
      {
        total: 1000,
        assets: {
          ADA: { holdings: -10, value: -100 },
          ETH: { holdings: -5, value: -50 },
        },
      },
    ])
    expect(getNegativeHoldingsWarnings(state)).toEqual([
      {
        symbol: "ADA",
        suggestedTradeSymbol: "ADA/USDT",
        exchangeConfigLabel: undefined,
      },
      {
        symbol: "ETH",
        suggestedTradeSymbol: "ETH/USDT",
        exchangeConfigLabel: undefined,
      },
    ])
  })

  it("ignores zero and positive holdings", () => {
    const state = makeHistoryState([
      {
        total: 1000,
        assets: {
          USDT: { holdings: 100, value: 100 },
          BTC: { holdings: 0, value: 0 },
        },
      },
    ])
    expect(getNegativeHoldingsWarnings(state)).toEqual([])
  })

  it("ignores negative holdings below the portfolio significance threshold", () => {
    const state = makeHistoryState([
      {
        total: 1000,
        assets: {
          ADA: { holdings: -1, value: -5 },
        },
      },
    ])
    expect(getNegativeHoldingsWarnings(state)).toEqual([])
  })

  it("warns when negative holdings exceed the portfolio significance threshold", () => {
    const state = makeHistoryState([
      {
        total: 1000,
        assets: {
          ADA: { holdings: -1, value: -50 },
        },
      },
    ])
    expect(getNegativeHoldingsWarnings(state)).toEqual([
      {
        symbol: "ADA",
        suggestedTradeSymbol: "ADA/USDT",
        exchangeConfigLabel: undefined,
      },
    ])
  })

  it("infers SOL/USDC via holdings when SOL has no priced value", () => {
    const state = makeHistoryState([
      {
        total: 1000,
        assets: {
          SOL: { holdings: 0, value: 0 },
          USDC: { holdings: 1000, value: 1000 },
        },
      },
      {
        total: 1000,
        assets: {
          SOL: { holdings: 10, value: 0 },
          USDC: { holdings: -50, value: 950 },
        },
      },
    ])
    expect(getNegativeHoldingsWarnings(state)).toEqual([
      {
        symbol: "USDC",
        suggestedTradeSymbol: "SOL/USDC",
        exchangeConfigLabel: undefined,
      },
    ])
  })

  it("warns with quote-only suggestion when only USDC is in the portfolio", () => {
    const state = makeHistoryState([
      {
        total: 1000,
        assets: {
          USDC: { holdings: -50, value: -50 },
        },
      },
    ])
    expect(getNegativeHoldingsWarnings(state)).toEqual([
      {
        symbol: "USDC",
        suggestedTradeSymbol: "/USDC",
        exchangeConfigLabel: undefined,
      },
    ])
  })

  it("suggests quote only when quote delta matching fails", () => {
    const state = makeHistoryState([
      {
        total: 1000,
        assets: {
          ALGO: { holdings: 100, value: 0 },
          SOL: { holdings: 10, value: 0 },
          USDC: { holdings: 1000, value: 1000 },
        },
      },
      {
        total: 1000,
        assets: {
          ALGO: { holdings: 100, value: 0 },
          SOL: { holdings: 10, value: 0 },
          USDC: { holdings: -200, value: 800 },
        },
      },
    ])
    expect(getNegativeHoldingsWarnings(state)).toEqual([
      {
        symbol: "USDC",
        suggestedTradeSymbol: "/USDC",
        exchangeConfigLabel: undefined,
      },
    ])
  })

  it("does not suggest a random pair from unchanged holdings", () => {
    const state = makeHistoryState([
      {
        total: 1000,
        assets: {
          SOL: { holdings: 10, value: 0 },
          USDC: { holdings: 1000, value: 1000 },
        },
      },
      {
        total: 1000,
        assets: {
          SOL: { holdings: 10, value: 0 },
          USDC: { holdings: -200, value: 800 },
        },
      },
    ])
    expect(getNegativeHoldingsWarnings(state)).toEqual([
      {
        symbol: "USDC",
        suggestedTradeSymbol: "/USDC",
        exchangeConfigLabel: undefined,
      },
    ])
  })

  it("falls back to detected quote market for crypto without counterparty", () => {
    const state = makeHistoryState([
      {
        total: 1000,
        assets: {
          ADA: { holdings: -10, value: -100 },
          USDC: { holdings: 500, value: 500 },
        },
      },
    ])
    expect(getNegativeHoldingsWarnings(state)).toEqual([
      {
        symbol: "ADA",
        suggestedTradeSymbol: "ADA/USDC",
        exchangeConfigLabel: undefined,
      },
    ])
  })

  it("infers SOL/USDT when quote went negative and SOL increased", () => {
    const state = makeHistoryState([
      {
        total: 1000,
        assets: {
          SOL: { holdings: 0, value: 0 },
          USDT: { holdings: 1000, value: 1000 },
        },
      },
      {
        total: 1000,
        assets: {
          SOL: { holdings: 5, value: 200 },
          USDT: { holdings: -50, value: 800 },
        },
      },
    ])
    expect(getNegativeHoldingsWarnings(state)).toEqual([
      {
        symbol: "USDT",
        suggestedTradeSymbol: "SOL/USDT",
        exchangeConfigLabel: undefined,
      },
    ])
  })

  it("infers ADA/USDT when ADA went negative and USDT increased", () => {
    const state = makeHistoryState([
      {
        total: 1000,
        assets: {
          ADA: { holdings: 10, value: 400 },
          USDT: { holdings: 600, value: 600 },
        },
      },
      {
        total: 1000,
        assets: {
          ADA: { holdings: -2, value: 200 },
          USDT: { holdings: 800, value: 800 },
        },
      },
    ])
    expect(getNegativeHoldingsWarnings(state)).toEqual([
      {
        symbol: "ADA",
        suggestedTradeSymbol: "ADA/USDT",
        exchangeConfigLabel: undefined,
      },
    ])
  })

  it("falls back to symbol over reference market when there is no previous day", () => {
    const state = makeHistoryState([
      {
        total: 1000,
        assets: {
          ADA: { holdings: -10, value: -100 },
        },
      },
    ])
    expect(getNegativeHoldingsWarnings(state)).toEqual([
      {
        symbol: "ADA",
        suggestedTradeSymbol: "ADA/USDT",
        exchangeConfigLabel: undefined,
      },
    ])
  })

  it("falls back when no counterparty asset increased on the trigger day", () => {
    const state = makeHistoryState([
      {
        total: 1000,
        assets: {
          ADA: { holdings: 10, value: 1000 },
        },
      },
      {
        total: 1000,
        assets: {
          ADA: { holdings: -10, value: -100 },
        },
      },
    ])
    expect(getNegativeHoldingsWarnings(state)).toEqual([
      {
        symbol: "ADA",
        suggestedTradeSymbol: "ADA/USDT",
        exchangeConfigLabel: undefined,
      },
    ])
  })

  it("includes exchange config label when account is linked", () => {
    const account = {
      id: "acc-1",
      name: "Kraken real",
      is_simulated: false,
      created_at: "2024-01-01T00:00:00Z",
      specifics: {
        actual_instance: {
          account_type: "exchange",
          remote_account_id: "remote-1",
          exchange_config_ids: ["cfg-kraken"],
        },
      },
    } as Account
    const exchangeConfigs = [
      {
        id: "cfg-kraken",
        name: "Kraken main",
        exchange: "kraken",
        sandboxed: false,
      },
    ]
    const state = makeHistoryState([
      {
        total: 1000,
        assets: {
          ADA: { holdings: -10, value: -100 },
        },
      },
    ])
    expect(getNegativeHoldingsWarnings(state, "USDT", account, exchangeConfigs)).toEqual([
      {
        symbol: "ADA",
        suggestedTradeSymbol: "ADA/USDT",
        exchangeConfigLabel: "Kraken main",
      },
    ])
  })
})
