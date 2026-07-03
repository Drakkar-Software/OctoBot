import { useState } from "react"

import { ScrollableTooltipContent } from "@/components/Common/Tables/ScrollableTooltipContent"
import { Tooltip, TooltipTrigger } from "@/components/ui/tooltip"

type AutomationTradingCountCellProps = {
  count: number
  getTooltip: () => string | null
}

export function AutomationTradingCountCell({
  count,
  getTooltip,
}: AutomationTradingCountCellProps) {
  const [tooltip, setTooltip] = useState<string | null>(null)

  if (count <= 0) {
    return <>0</>
  }

  return (
    <Tooltip
      onOpenChange={(isOpen) => {
        if (isOpen) {
          setTooltip(getTooltip())
        } else {
          setTooltip(null)
        }
      }}
    >
      <TooltipTrigger asChild>
        <span className="cursor-default">{count}</span>
      </TooltipTrigger>
      {tooltip ? (
        <ScrollableTooltipContent>{tooltip}</ScrollableTooltipContent>
      ) : null}
    </Tooltip>
  )
}
