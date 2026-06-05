import type { ReactNode } from "react"

import { TooltipContent } from "@/components/ui/tooltip"
import { SCROLLABLE_TOOLTIP_INNER_CLASS } from "@/lib/debug/constants"
import { cn } from "@/lib/utils"

type ScrollableTooltipContentProps = {
  children: ReactNode
  side?: "top" | "right" | "bottom" | "left"
  className?: string
}

export function ScrollableTooltipContent({
  children,
  side = "top",
  className,
}: ScrollableTooltipContentProps) {
  return (
    <TooltipContent
      side={side}
      className={cn("max-w-3xl p-0 [text-wrap:wrap]", className)}
    >
      <div className={SCROLLABLE_TOOLTIP_INNER_CLASS}>{children}</div>
    </TooltipContent>
  )
}
