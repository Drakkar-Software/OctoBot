import { ScrollableTooltipContent } from "@/components/Common/Tables/ScrollableTooltipContent"
import { Tooltip, TooltipTrigger } from "@/components/ui/tooltip"

type AutomationTradingCountCellProps = {
  count: number
  tooltip: string | null
}

export function AutomationTradingCountCell({
  count,
  tooltip,
}: AutomationTradingCountCellProps) {
  if (count <= 0) {
    return <>0</>
  }
  if (!tooltip) {
    return <>{count}</>
  }
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="cursor-default">{count}</span>
      </TooltipTrigger>
      <ScrollableTooltipContent>{tooltip}</ScrollableTooltipContent>
    </Tooltip>
  )
}
