import { ScrollableTooltipContent } from "@/components/Common/Tables/ScrollableTooltipContent"
import { Tooltip, TooltipTrigger } from "@/components/ui/tooltip"
import { ERROR_DETAILS_DISPLAY_LENGTH } from "@/lib/debug/constants"

type TruncatedTextWithTooltipProps = {
  text: string
  maxLength?: number
  className?: string
}

export function TruncatedTextWithTooltip({
  text,
  maxLength = ERROR_DETAILS_DISPLAY_LENGTH,
  className,
}: TruncatedTextWithTooltipProps) {
  if (text === "—" || text.length <= maxLength) {
    return <span className={className}>{text}</span>
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className={`cursor-default ${className ?? ""}`}>
          {text.slice(0, maxLength)}…
        </span>
      </TooltipTrigger>
      <ScrollableTooltipContent>{text}</ScrollableTooltipContent>
    </Tooltip>
  )
}
