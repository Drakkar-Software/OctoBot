import { useMemo, useRef, type TextareaHTMLAttributes } from "react"

import { cn } from "@/lib/utils"

const LINE_CLASS = "font-mono text-xs leading-5"

export function LineNumberTextarea({
  value = "",
  className,
  textareaClassName,
  onScroll,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement> & {
  textareaClassName?: string
}) {
  const gutterRef = useRef<HTMLDivElement>(null)
  const text = String(value)
  const lineCount = useMemo(
    () => Math.max(1, text.split("\n").length),
    [text],
  )

  const handleScroll = (event: React.UIEvent<HTMLTextAreaElement>) => {
    if (gutterRef.current) {
      gutterRef.current.scrollTop = event.currentTarget.scrollTop
    }
    onScroll?.(event)
  }

  return (
    <div
      className={cn(
        "flex min-h-[220px] overflow-hidden rounded-md border bg-muted focus-within:ring-1 focus-within:ring-ring",
        className,
      )}
    >
      <div
        className="flex w-10 shrink-0 flex-col overflow-hidden border-r border-border/60 bg-muted/80"
        aria-hidden
      >
        <div ref={gutterRef} className="overflow-hidden px-2 py-2 text-right">
          {Array.from({ length: lineCount }, (_, index) => (
            <div
              key={index + 1}
              className={cn(LINE_CLASS, "text-muted-foreground select-none")}
            >
              {index + 1}
            </div>
          ))}
        </div>
      </div>
      <textarea
        value={value}
        onScroll={handleScroll}
        className={cn(
          "min-h-[220px] w-full flex-1 resize-y border-0 bg-transparent px-3 py-2 focus:outline-none focus:ring-0",
          LINE_CLASS,
          textareaClassName,
        )}
        spellCheck={false}
        {...props}
      />
    </div>
  )
}
