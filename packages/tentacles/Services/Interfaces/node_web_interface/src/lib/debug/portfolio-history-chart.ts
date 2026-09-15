import type {
  PortfolioHistoricalValue,
  PortfolioHistoricalValuesState,
} from "@/lib/debug/portfolio-historical-values-types"
import { formatDateTime } from "@/lib/format-datetime"

export function portfolioHistoryToChartPoints(
  historyValues: PortfolioHistoricalValue[],
) {
  return historyValues.map((historyValue) => ({
    x: Date.parse(historyValue.timestamp),
    y: historyValue.total,
    historyValue,
  }))
}

export function formatPortfolioHistoryTooltip(
  historyValue: PortfolioHistoricalValue,
  unit: string,
) {
  const assetRows =
    historyValue.assets?.flatMap((assetsForType) => assetsForType.assets ?? []) ??
    []
  const assetsSortedByValue = [...assetRows].sort(
    (leftAsset, rightAsset) => rightAsset.value - leftAsset.value,
  )

  return {
    timestampLabel: formatDateTime(historyValue.timestamp),
    totalLabel: `${historyValue.total.toLocaleString(undefined, {
      maximumFractionDigits: 2,
    })} ${unit}`,
    valueColumnLabel: `Value (${unit})`,
    assetRows: assetsSortedByValue.map((asset) => ({
      symbol: asset.symbol,
      holdings: asset.holdings.toLocaleString(undefined, {
        maximumFractionDigits: 8,
      }),
      value: asset.value.toLocaleString(undefined, {
        maximumFractionDigits: 2,
      }),
    })),
  }
}

export function getPortfolioHistoryChartPoints(state?: PortfolioHistoricalValuesState) {
  const historyValues = state?.history?.values ?? []
  return portfolioHistoryToChartPoints(historyValues)
}
