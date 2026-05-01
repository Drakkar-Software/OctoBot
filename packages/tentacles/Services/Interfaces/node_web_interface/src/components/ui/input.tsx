import * as React from "react"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "border-rule h-[52px] w-full min-w-0 rounded-pill border bg-input px-5 py-1 text-base text-foreground shadow-none transition-[color,box-shadow] outline-none",
        "placeholder:text-muted-foreground selection:bg-primary selection:text-primary-foreground",
        "file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground",
        "disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50",
        "focus-visible:border-frost focus-visible:ring-2 focus-visible:ring-frost/30",
        "aria-invalid:border-neg aria-invalid:ring-neg/20",
        className
      )}
      {...props}
    />
  )
}

export { Input }
