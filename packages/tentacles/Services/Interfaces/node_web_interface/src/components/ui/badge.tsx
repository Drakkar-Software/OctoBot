import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center justify-center rounded-pill border px-2.5 py-1 text-xs font-medium w-fit whitespace-nowrap shrink-0 [&>svg]:size-3 gap-1 [&>svg]:pointer-events-none transition-[color,box-shadow] overflow-hidden",
  {
    variants: {
      variant: {
        default:
          "border-rule-soft bg-surface-soft text-foreground",
        secondary:
          "border-rule-soft bg-surface-soft text-muted-foreground",
        destructive:
          "border-transparent bg-neg/15 text-neg",
        outline:
          "border-rule text-foreground",
        pos:
          "border-transparent bg-pos/15 text-pos",
        neg:
          "border-transparent bg-neg/15 text-neg",
        warn:
          "border-transparent bg-warn/15 text-warn",
        frost:
          "border-transparent bg-accent/15 text-accent",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant,
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "span"

  return (
    <Comp
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
