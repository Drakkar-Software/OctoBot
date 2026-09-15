import { Loader2 } from "lucide-react"
import { useMemo } from "react"

import { SvgLineChart } from "@/components/Common/charts/SvgLineChart"
import {
  formatPortfolioHistoryTooltip,
  getPortfolioHistoryChartPoints,
} from "@/lib/debug/portfolio-history-chart"
import type { PortfolioHistoricalValuesState } from "@/lib/debug/portfolio-historical-values-types"

type PortfolioHistoryChartProps = {
  state: PortfolioHistoricalValuesState | undefined
  isLoading: boolean
  error?: unknown
  isImportedMode?: boolean
}

export function PortfolioHistoryChart({
  state,
  isLoading,
  error,
  isImportedMode = false,
}: PortfolioHistoryChartProps) {
  const chartData = useMemo(
    () => getPortfolioHistoryChartPoints(state),
    [state],
  )
  const chartPoints = useMemo(
    () => chartData.map((point) => ({ x: point.x, y: point.y })),
    [chartData],
  )
  const unit = state?.history?.unit ?? "USDT"

  if (isImportedMode) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        History unavailable in imported snapshot.
      </p>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" />
        Loading history…
      </div>
    )
  }

  if (error) {
    return (
      <p className="text-sm text-destructive py-4">
        Failed to load portfolio history.
      </p>
    )
  }

  return (
    <SvgLineChart
      points={chartPoints}
      ariaLabel="Portfolio historical value chart"
      emptyMessage="No historical data"
      renderTooltip={(_point, index) => {
        const historyValue = chartData[index]?.historyValue
        if (!historyValue) {
          return null
        }
        const tooltip = formatPortfolioHistoryTooltip(historyValue, unit)
        return (
          <div className="space-y-2">
            <div className="font-medium">{tooltip.timestampLabel}</div>
            <div>Total: {tooltip.totalLabel}</div>
            {tooltip.assetRows.length > 0 ? (
              <table className="w-full border-collapse">
                <thead>
                  <tr className="text-left text-muted-foreground">
                    <th className="pr-3 font-normal">Asset</th>
                    <th className="pr-3 font-normal">Holdings</th>
                    <th className="font-normal">{tooltip.valueColumnLabel}</th>
                  </tr>
                </thead>
                <tbody>
                  {tooltip.assetRows.map((assetRow) => (
                    <tr key={assetRow.symbol}>
                      <td className="pr-3">{assetRow.symbol}</td>
                      <td className="pr-3 font-mono">{assetRow.holdings}</td>
                      <td className="font-mono">{assetRow.value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-muted-foreground">No holdings breakdown.</p>
            )}
          </div>
        )
      }}
    />
  )
}
