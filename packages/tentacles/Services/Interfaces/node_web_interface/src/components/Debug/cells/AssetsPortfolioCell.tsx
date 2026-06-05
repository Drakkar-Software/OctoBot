import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { COMPACT_TOOLTIP_CONTENT_CLASS } from "@/lib/debug/constants"
import {
  formatAssetsPortfolioTooltip,
  formatAssetsSymbolsSummary,
  type AssetsListEntry,
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
      <TooltipContent side="top" className={COMPACT_TOOLTIP_CONTENT_CLASS}>
        {tooltip}
      </TooltipContent>
    </Tooltip>
  )
}
