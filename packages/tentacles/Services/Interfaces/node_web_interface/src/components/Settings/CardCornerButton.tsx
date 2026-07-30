import type { LucideIcon } from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export function CardCornerButton({
  icon: Icon,
  label,
  onClick,
  variant = "default",
}: {
  icon: LucideIcon
  label: string
  onClick: () => void
  variant?: "default" | "destructive"
}) {
  return (
    <div className="absolute right-4 top-4">
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            className={`rounded-md p-1.5 text-muted-foreground transition-colors ${
              variant === "destructive"
                ? "hover:bg-destructive/10 hover:text-destructive"
                : "hover:bg-accent/10 hover:text-accent"
            }`}
            aria-label={label}
            onClick={onClick}
          >
            <Icon className="size-5" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="left">{label}</TooltipContent>
      </Tooltip>
    </div>
  )
}
