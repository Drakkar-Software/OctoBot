import type { UserAction } from "@/client"
import { ScrollableTooltipContent } from "@/components/Common/Tables/ScrollableTooltipContent"
import { Tooltip, TooltipTrigger } from "@/components/ui/tooltip"
import {
  formatSignalExecutionResultTooltipLines,
  formatSignalExecutionResultsSummary,
  getSignalExecutionResults,
} from "@/lib/debug/signal-execution-result"

type SignalExecutionResultsCellProps = {
  result: UserAction["result"]
}

export function SignalExecutionResultsCell({
  result,
}: SignalExecutionResultsCellProps) {
  const signalExecutionResults = getSignalExecutionResults(result)
  const summary = formatSignalExecutionResultsSummary(signalExecutionResults)
  if (summary === "—") {
    return <span>—</span>
  }

  const tooltipText = formatSignalExecutionResultTooltipLines(
    signalExecutionResults,
  ).join("\n")

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="cursor-default truncate max-w-[10rem] block">
          {summary}
        </span>
      </TooltipTrigger>
      <ScrollableTooltipContent className="whitespace-pre-line">
        {tooltipText}
      </ScrollableTooltipContent>
    </Tooltip>
  )
}
