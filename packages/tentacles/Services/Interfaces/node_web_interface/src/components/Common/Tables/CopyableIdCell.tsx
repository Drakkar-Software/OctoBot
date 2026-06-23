import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { copyTextToClipboard } from "@/lib/clipboard"
import { formatIdDisplay } from "@/lib/format-id"

type CopyableIdCellProps = {
  id: string
}

export function CopyableIdCell({ id }: CopyableIdCellProps) {
  const copy = () => {
    copyTextToClipboard(id, id)
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="font-mono text-xs cursor-pointer hover:text-foreground"
          aria-label={`Copy ID ${id}`}
          onClick={copy}
        >
          {formatIdDisplay(id)}
        </button>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        className="font-mono text-xs max-w-md break-all p-3"
      >
        {id}
      </TooltipContent>
    </Tooltip>
  )
}
