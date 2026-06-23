import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  type AssetsListEntry,
  formatAssetsPortfolioTooltip,
  formatAssetsSymbolsSummary,
} from "@/lib/debug/display-utils"

type AssetsPortfolioCellProps = {
  assets: Array<AssetsListEntry> | null | undefined
  maxVisible?: number
}

export function AssetsPortfolioCell({
  assets,
  maxVisible = 3,
}: AssetsPortfolioCellProps) {
  const summary = formatAssetsSymbolsSummary(assets, maxVisible)
  const tooltip = formatAssetsPortfolioTooltip(assets)

  if (!tooltip) {
    return summary
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="cursor-default font-mono text-xs">{summary}</span>
      </TooltipTrigger>
      <TooltipContent side="top" className="tooltip-compact-content">
        {tooltip}
      </TooltipContent>
    </Tooltip>
  )
}
