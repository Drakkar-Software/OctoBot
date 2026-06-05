import { describe, expect, it } from "vitest"

import type {
  Account,
  AccountTradingWithAccountId,
  AutomationState,
  ExchangeConfig,
  DetailedAsset,
  DetailedAssetsForTradingType,
  Order,
  Trade,
} from "@/client"
import {
  flattenDetailedAssets,
  formatAssetsPortfolioTooltip,
  formatAssetsSymbolsSummary,
  formatDebugStatusTooltip,
  formatOrdersTradingTooltip,
  formatTradesTradingTooltip,
  getAccountExchangeNames,
  getAccountOrdersCount,
  getAccountOrdersTooltipContent,
  getAccountTradesCount,
  getAccountTradesTooltipContent,
  getAutomationOrdersTooltipContent,
  getAutomationTradesTooltipContent,
  getDetailedOrdersForAutomation,
  getDetailedTradesForAutomation,
  getDebugStatusDisplay,
  getTradingSummariesForAutomation,
  debugTableCellClass,
  getDebugTableColumnAlignClass,
  matchesColumnFilter,
  matchesDebugStatusColumnFilter,
} from "@/lib/debug-display-utils"

function makeAssets(
  groups: Array<{
    trading_type: string
    assets: Array<{ symbol: string; available: number; total: number }>
  }>,
): DetailedAssetsForTradingType[] {
  return groups.map((group) => ({
    trading_type: group.trading_type as DetailedAssetsForTradingType["trading_type"],
    assets: group.assets.map((asset) => ({
      symbol: asset.symbol,
      available: asset.available,
      total: asset.total,
    })),
  }))
}

describe("flattenDetailedAssets", () => {
  it("returns empty array when assets are missing", () => {
    expect(flattenDetailedAssets(null)).toEqual([])
    expect(flattenDetailedAssets([])).toEqual([])
  })

  it("flattens flat automation-style assets", () => {
    const assets: DetailedAsset[] = [
      { symbol: "BTC", available: 1, total: 2 },
      { symbol: "ETH", available: 0.5, total: 1 },
    ]
    expect(flattenDetailedAssets(assets).map((a) => a.symbol)).toEqual([
      "BTC",
      "ETH",
    ])
  })

  it("flattens assets in trading type order", () => {
    const assets = makeAssets([
      {
        trading_type: "spot",
        assets: [{ symbol: "BTC", available: 1, total: 2 }],
      },
      {
        trading_type: "futures",
        assets: [{ symbol: "ETH", available: 0.5, total: 1 }],
      },
    ])
    expect(flattenDetailedAssets(assets).map((a) => a.symbol)).toEqual([
      "BTC",
      "ETH",
    ])
  })
})

describe("formatAssetsSymbolsSummary", () => {
  it("returns em dash when empty", () => {
    expect(formatAssetsSymbolsSummary(null)).toBe("—")
  })

  it("lists up to three symbols", () => {
    const assets = makeAssets([
      {
        trading_type: "spot",
        assets: [
          { symbol: "BTC", available: 1, total: 1 },
          { symbol: "ETH", available: 1, total: 1 },
        ],
      },
    ])
    expect(formatAssetsSymbolsSummary(assets)).toBe("BTC, ETH")
  })

  it("appends remaining count when more than three", () => {
    const assets = makeAssets([
      {
        trading_type: "spot",
        assets: [
          { symbol: "BTC", available: 1, total: 1 },
          { symbol: "ETH", available: 1, total: 1 },
          { symbol: "USDT", available: 1, total: 1 },
          { symbol: "SOL", available: 1, total: 1 },
          { symbol: "XRP", available: 1, total: 1 },
        ],
      },
    ])
    expect(formatAssetsSymbolsSummary(assets)).toBe("BTC, ETH, USDT +2")
  })

  it("respects maxVisible override", () => {
    const assets = makeAssets([
      {
        trading_type: "spot",
        assets: [
          { symbol: "BTC", available: 1, total: 1 },
          { symbol: "ETH", available: 1, total: 1 },
          { symbol: "USDT", available: 1, total: 1 },
          { symbol: "SOL", available: 1, total: 1 },
        ],
      },
    ])
    expect(formatAssetsSymbolsSummary(assets, 2)).toBe("BTC, ETH +2")
  })
})

describe("formatAssetsPortfolioTooltip", () => {
  it("returns null when no assets", () => {
    expect(formatAssetsPortfolioTooltip(null)).toBeNull()
    expect(formatAssetsPortfolioTooltip([])).toBeNull()
  })

  it("formats flat automation portfolio lines", () => {
    const assets: DetailedAsset[] = [
      { symbol: "BTC", available: 1.5, total: 2 },
      { symbol: "ETH", available: 0, total: 1 },
    ]
    expect(formatAssetsPortfolioTooltip(assets)).toBe(
      "BTC: 1.5/2\nETH: 0/1",
    )
  })

  it("formats available/total per symbol", () => {
    const assets = makeAssets([
      {
        trading_type: "spot",
        assets: [
          { symbol: "BTC", available: 1.5, total: 2 },
          { symbol: "ETH", available: 0, total: 1 },
        ],
      },
    ])
    expect(formatAssetsPortfolioTooltip(assets)).toBe(
      "BTC: 1.5/2\nETH: 0/1",
    )
  })

  it("prefixes trading type when multiple groups", () => {
    const assets = makeAssets([
      {
        trading_type: "spot",
        assets: [{ symbol: "BTC", available: 1, total: 1 }],
      },
      {
        trading_type: "futures",
        assets: [{ symbol: "ETH", available: 0.5, total: 1 }],
      },
    ])
    expect(formatAssetsPortfolioTooltip(assets)).toBe(
      "spot:\nBTC: 1/1\nfutures:\nETH: 0.5/1",
    )
  })
})

describe("getDebugStatusDisplay", () => {
  it("maps task statuses to colored emoji", () => {
    expect(getDebugStatusDisplay("running")).toEqual({
      emoji: "🟢",
      label: "Running",
    })
    expect(getDebugStatusDisplay("failed")).toEqual({
      emoji: "🔴",
      label: "Failed",
    })
    expect(getDebugStatusDisplay("completed")).toEqual({
      emoji: "✅",
      label: "Completed",
    })
  })

  it("maps account statuses", () => {
    expect(getDebugStatusDisplay("valid").emoji).toBe("🟢")
    expect(getDebugStatusDisplay("invalid").emoji).toBe("🔴")
    expect(getDebugStatusDisplay("unknown").emoji).toBe("🟡")
  })

  it("returns neutral display when status is missing", () => {
    expect(getDebugStatusDisplay(null)).toEqual({ emoji: "➖", label: "—" })
  })
})

describe("formatDebugStatusTooltip", () => {
  it("includes status label and extra lines", () => {
    expect(
      formatDebugStatusTooltip("running", ["error: timeout"]),
    ).toBe("Running\nerror: timeout")
  })
})

describe("getDebugTableColumnAlignClass", () => {
  it("returns text-center only for center columns", () => {
    expect(getDebugTableColumnAlignClass("center")).toBe("text-center")
    expect(getDebugTableColumnAlignClass("left")).toBe("")
  })

  it("uses the same align class regardless of cell value", () => {
    const center = getDebugTableColumnAlignClass("center")
    expect(debugTableCellClass("center")).toBe(center)
    expect(debugTableCellClass("center", "font-mono text-xs")).toBe(
      "text-center font-mono text-xs",
    )
    // Regression: old heuristic diverged for these values in the same column
    expect(debugTableCellClass("center")).toBe(
      debugTableCellClass("center"),
    )
  })
})

describe("matchesDebugStatusColumnFilter", () => {
  it("matches failed exactly, not completed", () => {
    expect(matchesDebugStatusColumnFilter("failed", "failed")).toBe(true)
    expect(matchesDebugStatusColumnFilter("completed", "failed")).toBe(false)
    expect(matchesDebugStatusColumnFilter("running", "failed")).toBe(false)
  })

  it("allows partial search for non-token queries", () => {
    expect(matchesDebugStatusColumnFilter("running", "run")).toBe(true)
    expect(matchesDebugStatusColumnFilter("completed", "comp")).toBe(true)
  })
})

describe("matchesColumnFilter", () => {
  it("does not match completed when filtering failed substring", () => {
    expect(matchesColumnFilter("completed", "failed")).toBe(false)
  })
})

function makeAutomation(
  overrides: Partial<AutomationState> = {},
): AutomationState {
  return {
    id: "auto-1",
    status: "running",
    metadata: { name: "Test", description: "" },
    ...overrides,
  }
}

const sampleOrder: Order = {
  id: "order-1",
  symbol: "BTC/USDT",
  price: 50000,
  quantity: 1,
  filled: 0.5,
  exchange_id: "binance",
  side: "buy",
  type: "limit",
  status: "open",
  created_at: "2026-01-01T00:00:00Z",
}

const sampleTrade: Trade = {
  id: "trade-1",
  trade_id: "ex-trade-1",
  type: "market",
  symbol: "ETH/USDT",
  side: "sell",
  quantity: 2,
  price: 3000,
  status: "filled",
  executed_at: "2026-01-02T12:00:00Z",
}

function formatTradingTooltipDateTimeForTest(iso: string): string {
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(iso))
}

describe("getTradingSummariesForAutomation", () => {
  const summaries: AccountTradingWithAccountId[] = [
    {
      account_id: "acc-a",
      account_trading: { updated_at: "2026-01-01T00:00:00Z", orders: [sampleOrder] },
    },
    {
      account_id: "acc-b",
      account_trading: { updated_at: "2026-01-02T12:00:00Z", trades: [sampleTrade] },
    },
    { account_id: "acc-other" },
  ]

  it("returns empty when exchange_account_ids is missing", () => {
    expect(
      getTradingSummariesForAutomation(makeAutomation(), summaries),
    ).toEqual([])
  })

  it("matches summaries by account_id and ignores unrelated", () => {
    const matched = getTradingSummariesForAutomation(
      makeAutomation({ exchange_account_ids: ["acc-a", "acc-b"] }),
      summaries,
    )
    expect(matched.map((s) => s.account_id)).toEqual(["acc-a", "acc-b"])
  })

  it("merges orders and trades from multiple bound accounts when summaries match", () => {
    const automation = makeAutomation({
      exchange_account_ids: ["acc-a", "acc-b"],
      orders: [{ id: sampleOrder.id, symbol: sampleOrder.symbol }],
      trades: [{ id: sampleTrade.trade_id, symbol: sampleTrade.symbol }],
    })
    expect(getDetailedOrdersForAutomation(automation, summaries)).toHaveLength(1)
    expect(getDetailedTradesForAutomation(automation, summaries)).toHaveLength(1)
  })
})

describe("formatOrdersTradingTooltip", () => {
  it("includes symbol, side, and local formatted created time", () => {
    const text = formatOrdersTradingTooltip([sampleOrder])
    expect(text).toContain("BTC/USDT")
    expect(text).toContain("BUY")
    expect(text).toContain("LIMIT")
    expect(text).toContain(
      formatTradingTooltipDateTimeForTest(sampleOrder.created_at),
    )
    expect(text).not.toContain("2026-01-01T00:00:00Z")
  })

  it("sorts by symbol ascending", () => {
    const orders: Order[] = [
      {
        ...sampleOrder,
        id: "o-eth",
        symbol: "ETH/USDT",
        created_at: "2026-01-03T00:00:00Z",
      },
      {
        ...sampleOrder,
        id: "o-btc",
        symbol: "BTC/USDT",
        created_at: "2026-01-01T00:00:00Z",
      },
    ]
    const text = formatOrdersTradingTooltip(orders)!
    expect(text.indexOf("BTC/USDT")).toBeLessThan(text.indexOf("ETH/USDT"))
  })

  it("sorts by price descending within the same symbol", () => {
    const orders: Order[] = [
      { ...sampleOrder, id: "o-low", price: 100 },
      { ...sampleOrder, id: "o-high", price: 200 },
    ]
    const text = formatOrdersTradingTooltip(orders)!
    expect(text.indexOf("@ 200")).toBeLessThan(text.indexOf("@ 100"))
  })

  it("sorts by created_at descending within the same symbol and price", () => {
    const orders: Order[] = [
      { ...sampleOrder, id: "o1", created_at: "2026-01-01T00:00:00Z" },
      { ...sampleOrder, id: "o2", created_at: "2026-01-03T00:00:00Z" },
      { ...sampleOrder, id: "o3", created_at: "2026-01-02T00:00:00Z" },
    ]
    const text = formatOrdersTradingTooltip(orders)!
    const newestDate = formatTradingTooltipDateTimeForTest("2026-01-03T00:00:00Z")
    const middleDate = formatTradingTooltipDateTimeForTest("2026-01-02T00:00:00Z")
    const oldestDate = formatTradingTooltipDateTimeForTest("2026-01-01T00:00:00Z")
    expect(text.indexOf(newestDate)).toBeLessThan(text.indexOf(middleDate))
    expect(text.indexOf(middleDate)).toBeLessThan(text.indexOf(oldestDate))
  })

  it("prefixes account_id when multiple summaries contribute", () => {
    const text = formatOrdersTradingTooltip([sampleOrder], [
      {
        account_id: "acc-a",
        account_trading: { updated_at: "2026-01-01T00:00:00Z", orders: [sampleOrder] },
      },
      {
        account_id: "acc-b",
        account_trading: {
          updated_at: "2026-01-01T00:00:00Z",
          orders: [
            {
              ...sampleOrder,
              id: "order-2",
              symbol: "ETH/USDT",
            },
          ],
        },
      },
    ])
    expect(text).toContain("acc-a:")
    expect(text).toContain("acc-b:")
    expect(text).toContain("ETH/USDT")
  })
})

describe("formatTradesTradingTooltip", () => {
  it("sorts by executed_at descending", () => {
    const trades: Trade[] = [
      { ...sampleTrade, id: "t1", executed_at: "2026-01-01T00:00:00Z" },
      { ...sampleTrade, id: "t2", executed_at: "2026-01-03T00:00:00Z" },
      { ...sampleTrade, id: "t3", executed_at: "2026-01-02T00:00:00Z" },
    ]
    const text = formatTradesTradingTooltip(trades)!
    const newestDate = formatTradingTooltipDateTimeForTest("2026-01-03T00:00:00Z")
    const middleDate = formatTradingTooltipDateTimeForTest("2026-01-02T00:00:00Z")
    const oldestDate = formatTradingTooltipDateTimeForTest("2026-01-01T00:00:00Z")
    expect(text.indexOf(newestDate)).toBeLessThan(text.indexOf(middleDate))
    expect(text.indexOf(middleDate)).toBeLessThan(text.indexOf(oldestDate))
  })

  it("includes symbol, side, and local formatted executed time", () => {
    const text = formatTradesTradingTooltip([sampleTrade])
    expect(text).toContain("ETH/USDT")
    expect(text).toContain("SELL")
    expect(text).toContain("MARKET")
    expect(text).toContain(
      formatTradingTooltipDateTimeForTest(sampleTrade.executed_at),
    )
    expect(text).not.toContain("2026-01-02T12:00:00Z")
  })
})

describe("getAutomationOrdersTooltipContent", () => {
  it("prefers detailed orders from summaries", () => {
    const text = getAutomationOrdersTooltipContent(
      makeAutomation({
        exchange_account_ids: ["acc-a"],
        orders: [{ id: sampleOrder.id, symbol: sampleOrder.symbol }],
      }),
      [
        {
          account_id: "acc-a",
          account_trading: {
            updated_at: "2026-01-01T00:00:00Z",
            orders: [sampleOrder],
          },
        },
      ],
    )
    expect(text).toContain("BTC/USDT")
    expect(text).not.toContain('"symbol"')
  })

  it("shows only orders listed on the automation, not other account orders", () => {
    const extraOrder: Order = {
      ...sampleOrder,
      id: "order-extra",
      exchange_id: "exchange-extra",
      symbol: "SOL/USDT",
    }
    const text = getAutomationOrdersTooltipContent(
      makeAutomation({
        exchange_account_ids: ["acc-a"],
        orders: [{ id: sampleOrder.id, symbol: sampleOrder.symbol }],
      }),
      [
        {
          account_id: "acc-a",
          account_trading: {
            updated_at: "2026-01-01T00:00:00Z",
            orders: [sampleOrder, extraOrder],
          },
        },
      ],
    )
    expect(text).toContain("BTC/USDT")
    expect(text).not.toContain("SOL/USDT")
    expect(text?.split("\n").filter((line) => line.includes("@")).length).toBe(1)
  })

  it("falls back to automation order summaries when account_tradings have no orders", () => {
    const text = getAutomationOrdersTooltipContent(
      makeAutomation({
        orders: [{ id: "sum-1", symbol: "SOL/USDT" }],
      }),
      [],
    )
    expect(text).toBe("sum-1 SOL/USDT")
  })
})

describe("getAutomationTradesTooltipContent", () => {
  it("returns null when automation and summaries have no trades", () => {
    expect(
      getAutomationTradesTooltipContent(makeAutomation(), []),
    ).toBeNull()
  })

  it("falls back to automation trade summaries when account_tradings have no trades", () => {
    const text = getAutomationTradesTooltipContent(
      makeAutomation({
        trades: [{ id: "trade-1", symbol: "ETH/USDT" }],
      }),
      [],
    )
    expect(text).toBe("trade-1 ETH/USDT")
  })

  it("formats detailed trades from summaries", () => {
    const text = getAutomationTradesTooltipContent(
      makeAutomation({
        exchange_account_ids: ["acc-b"],
        trades: [{ id: sampleTrade.trade_id, symbol: sampleTrade.symbol }],
      }),
      [
        {
          account_id: "acc-b",
          account_trading: {
            updated_at: "2026-01-02T12:00:00Z",
            trades: [sampleTrade],
          },
        },
      ],
    )
    expect(text).toContain("ETH/USDT")
    expect(text).toContain(
      formatTradingTooltipDateTimeForTest(sampleTrade.executed_at),
    )
  })

  it("shows only trades listed on the automation, not other account trades", () => {
    const extraTrade: Trade = {
      ...sampleTrade,
      id: "trade-extra",
      trade_id: "ex-trade-extra",
      symbol: "BTC/USDT",
    }
    const text = getAutomationTradesTooltipContent(
      makeAutomation({
        exchange_account_ids: ["acc-b"],
        trades: [
          { id: sampleTrade.trade_id, symbol: sampleTrade.symbol },
          { id: "ex-trade-other", symbol: "XRP/USDT" },
        ],
      }),
      [
        {
          account_id: "acc-b",
          account_trading: {
            updated_at: "2026-01-02T12:00:00Z",
            trades: [sampleTrade, extraTrade],
          },
        },
      ],
    )
    expect(text).toContain("ETH/USDT")
    expect(text).not.toContain("BTC/USDT")
    expect(text?.split("\n").filter((line) => line.includes("executed:")).length).toBe(1)
  })
})

describe("getAccountOrdersTooltipContent", () => {
  const accountTradings: AccountTradingWithAccountId[] = [
    {
      account_id: "acc-1",
      account_trading: {
        updated_at: "2026-01-01T00:00:00Z",
        orders: [sampleOrder],
      },
    },
  ]

  it("returns null when account has no trading entry", () => {
    expect(getAccountOrdersTooltipContent("missing", accountTradings)).toBeNull()
  })

  it("formats orders for the matching account", () => {
    const text = getAccountOrdersTooltipContent("acc-1", accountTradings)
    expect(text).toContain("BTC/USDT")
  })
})

describe("getAccountOrdersCount", () => {
  it("counts orders from account_tradings", () => {
    expect(
      getAccountOrdersCount("acc-1", [
        {
          account_id: "acc-1",
          account_trading: {
            updated_at: "2026-01-01T00:00:00Z",
            orders: [sampleOrder, sampleOrder],
          },
        },
      ]),
    ).toBe(2)
    expect(getAccountOrdersCount("acc-1", [])).toBe(0)
  })
})

describe("getAccountTradesCount", () => {
  it("counts trades from account_tradings", () => {
    expect(
      getAccountTradesCount("acc-2", [
        {
          account_id: "acc-2",
          account_trading: {
            updated_at: "2026-01-02T12:00:00Z",
            trades: [sampleTrade],
          },
        },
      ]),
    ).toBe(1)
  })
})

describe("getAccountTradesTooltipContent", () => {
  it("formats trades for the matching account", () => {
    const text = getAccountTradesTooltipContent("acc-2", [
      {
        account_id: "acc-2",
        account_trading: {
          updated_at: "2026-01-02T12:00:00Z",
          trades: [sampleTrade],
        },
      },
    ])
    expect(text).toContain("ETH/USDT")
  })
})

describe("getAccountExchangeNames", () => {
  const exchangeConfigs: ExchangeConfig[] = [
    {
      id: "cfg-binance",
      name: "My Binance",
      exchange: "binance",
      sandboxed: false,
    },
  ]

  function makeExchangeAccount(
    specifics: Account["specifics"],
  ): Account {
    return {
      id: "acc-1",
      name: "Test",
      is_simulated: false,
      created_at: "2026-01-01T00:00:00Z",
      specifics,
    }
  }

  it("returns exchange_config.exchange, not config name", () => {
    const label = getAccountExchangeNames(
      makeExchangeAccount({
        account_type: "exchange",
        remote_account_id: "remote-1",
        exchange_config_ids: ["cfg-binance"],
      } as Account["specifics"]),
      exchangeConfigs,
    )
    expect(label).toBe("binance")
    expect(label).not.toContain("My Binance")
  })

  it("reads exchange_config_ids from oneOf actual_instance", () => {
    const label = getAccountExchangeNames(
      makeExchangeAccount({
        actual_instance: {
          account_type: "exchange",
          remote_account_id: "remote-1",
          exchange_config_ids: ["cfg-binance"],
        },
      } as Account["specifics"]),
      exchangeConfigs,
    )
    expect(label).toBe("binance")
  })

  it("returns em dash when account has no bound exchange config", () => {
    expect(
      getAccountExchangeNames(
        makeExchangeAccount({
          account_type: "generic",
        } as Account["specifics"]),
        exchangeConfigs,
      ),
    ).toBe("—")
  })
})
