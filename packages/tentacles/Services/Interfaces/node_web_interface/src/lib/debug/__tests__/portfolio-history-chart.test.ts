import { describe, expect, it } from "vitest"

import { formatPortfolioHistoryTooltip } from "@/lib/debug/portfolio-history-chart"
import type { PortfolioHistoricalValue } from "@/lib/debug/portfolio-historical-values-types"

describe("formatPortfolioHistoryTooltip", () => {
  it("puts the unit in the column header and not in value cells", () => {
    const historyValue: PortfolioHistoricalValue = {
      timestamp: "2024-01-01T00:00:00Z",
      total: 1500.5,
      assets: [
        {
          trading_type: "spot",
          assets: [
            { symbol: "BTC", holdings: 1, value: 1000.25 },
            { symbol: "USDT", holdings: 500, value: 500.25 },
          ],
        },
      ],
    }

    const tooltip = formatPortfolioHistoryTooltip(historyValue, "USDT")

    expect(tooltip.valueColumnLabel).toBe("Value (USDT)")
    expect(tooltip.totalLabel).toContain("USDT")
    expect(tooltip.assetRows[0].value).not.toContain("USDT")
    expect(tooltip.assetRows[1].value).not.toContain("USDT")
  })

  it("orders assets by value descending", () => {
    const historyValue: PortfolioHistoricalValue = {
      timestamp: "2024-01-01T00:00:00Z",
      total: 1500.5,
      assets: [
        {
          trading_type: "spot",
          assets: [
            { symbol: "USDT", holdings: 500, value: 500.25 },
            { symbol: "ETH", holdings: 2, value: 750.5 },
            { symbol: "BTC", holdings: 1, value: 249.75 },
          ],
        },
      ],
    }

    const tooltip = formatPortfolioHistoryTooltip(historyValue, "USDT")

    expect(tooltip.assetRows.map((assetRow) => assetRow.symbol)).toEqual([
      "ETH",
      "USDT",
      "BTC",
    ])
  })
})
