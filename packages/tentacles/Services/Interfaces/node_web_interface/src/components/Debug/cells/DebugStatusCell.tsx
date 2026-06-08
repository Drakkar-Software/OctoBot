import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import {
  formatDebugStatusTooltip,
  getDebugStatusDisplay,
} from "@/lib/debug/display-utils"
import { cn } from "@/lib/utils"

type DebugStatusCellProps = {
  status: string | null | undefined
  extraTooltipLines?: string[]
  pulseWhenRunning?: boolean
}

export function DebugStatusCell({
  status,
  extraTooltipLines,
  pulseWhenRunning = false,
}: DebugStatusCellProps) {
  const { emoji, label } = getDebugStatusDisplay(status)
  const tooltip = formatDebugStatusTooltip(status, extraTooltipLines)
  const isLive = pulseWhenRunning && status?.toLowerCase() === "running"

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn(
            "cursor-default text-base leading-none",
            isLive && "animate-pulse",
          )}
          aria-label={label}
        >
          {emoji}
        </span>
      </TooltipTrigger>
      <TooltipContent side="top" className="tooltip-compact-content">
        {tooltip}
      </TooltipContent>
    </Tooltip>
  )
}
