import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

export function SeedPhraseWordGrid({ children }: { children: ReactNode }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">{children}</div>
  )
}

export type SeedPhraseWordGridCellProps = {
  index: number
  children: ReactNode
  className?: string
}

export function SeedPhraseWordGridCell({
  index,
  children,
  className,
}: SeedPhraseWordGridCellProps) {
  return (
    <div
      className={cn(
        "rounded-md border bg-muted px-3 py-2 text-sm font-mono",
        className,
      )}
    >
      <span className="text-muted-foreground mr-2">{index + 1}.</span>
      {children}
    </div>
  )
}
