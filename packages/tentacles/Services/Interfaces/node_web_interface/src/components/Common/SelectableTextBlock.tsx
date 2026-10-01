import type { FocusEvent, MouseEvent } from "react"

import { cn } from "@/lib/utils"

type SelectableTextBlockProps = {
  value: string
  ariaLabel: string
  multiline?: boolean
}

const selectableControlClassName = cn(
  "w-full cursor-text border-0 bg-transparent p-0 font-mono text-xs text-foreground",
  "break-all outline-none focus-visible:ring-0",
)

function selectAllInControl(
  event: FocusEvent<HTMLInputElement | HTMLTextAreaElement>,
): void {
  event.currentTarget.select()
}

function selectAllInControlOnClick(
  event: MouseEvent<HTMLInputElement | HTMLTextAreaElement>,
): void {
  event.currentTarget.select()
}

export function SelectableTextBlock({
  value,
  ariaLabel,
  multiline = false,
}: SelectableTextBlockProps) {
  const textareaRows = Math.max(2, value.split("\n").length)

  return (
    <div className="rounded-md border bg-muted px-2 py-1">
      {multiline ? (
        <textarea
          readOnly
          rows={textareaRows}
          value={value}
          aria-label={ariaLabel}
          className={cn(selectableControlClassName, "resize-none")}
          onFocus={selectAllInControl}
          onClick={selectAllInControlOnClick}
        />
      ) : (
        <input
          readOnly
          type="text"
          value={value}
          aria-label={ariaLabel}
          className={selectableControlClassName}
          onFocus={selectAllInControl}
          onClick={selectAllInControlOnClick}
        />
      )}
    </div>
  )
}
