import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  type DebugStatusDisplay,
  formatDebugStatusTooltip,
  getDebugStatusDisplay,
} from "@/lib/debug/display-utils"
import { cn } from "@/lib/utils"

type DebugStatusCellProps = {
  status: string | null | undefined
  display?: DebugStatusDisplay
  extraTooltipLines?: string[]
  pulseWhenRunning?: boolean
}

export function DebugStatusCell({
  status,
  display,
  extraTooltipLines,
  pulseWhenRunning = false,
}: DebugStatusCellProps) {
  const { emoji, label } = display ?? getDebugStatusDisplay(status)
  const tooltip = formatDebugStatusTooltip(status, extraTooltipLines)
  const isLive = pulseWhenRunning && status?.toLowerCase() === "running"

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          role="img"
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
