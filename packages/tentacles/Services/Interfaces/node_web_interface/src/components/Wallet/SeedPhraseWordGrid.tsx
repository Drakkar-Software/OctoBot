import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

/** Shared height and padding for reveal, quiz plaintext, quiz input, and confirmed cells. */
export const seedPhraseWordCellClassName =
  "flex h-11 min-h-11 items-center gap-2 rounded-md border bg-muted px-3 text-sm font-mono leading-none"

/** Reserve one error line so input rows align with plaintext rows in the grid. */
export function SeedPhraseWordGridSlot({
  cell,
  footer,
}: {
  cell: ReactNode
  footer?: ReactNode
}) {
  return (
    <div className="flex flex-col gap-1">
      {cell}
      <div className="min-h-5 text-sm leading-tight">
        {footer ?? (
          <span className="invisible select-none" aria-hidden="true">
            .
          </span>
        )}
      </div>
    </div>
  )
}

export function SeedPhraseWordGrid({ children }: { children: ReactNode }) {
  return (
    <div className="grid grid-cols-2 gap-x-2 gap-y-1 sm:grid-cols-3">
      {children}
    </div>
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
    <div className={cn(seedPhraseWordCellClassName, className)}>
      <span className="text-muted-foreground shrink-0 tabular-nums">
        {index + 1}.
      </span>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  )
}

/** Input styled to sit inside a word cell without changing cell height. */
export const seedPhraseQuizInputClassName =
  "h-8 w-full min-w-0 rounded-none border-0 bg-transparent p-0 text-sm font-mono shadow-none focus-visible:border-0 focus-visible:ring-0 aria-invalid:border-0 aria-invalid:ring-0"
