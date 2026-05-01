import { Slot, Slottable } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-pill text-sm font-medium tracking-tight transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-frost/50 focus-visible:ring-offset-1 active:scale-[.98] active:opacity-90",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground shadow-glow hover:bg-primary/90",
        destructive:
          "bg-neg/15 text-neg border border-neg/35 hover:bg-neg/20",
        outline:
          "border border-rule bg-surface-soft text-foreground hover:bg-surface-mid",
        secondary:
          "bg-surface-mid text-foreground hover:bg-surface-strong",
        ghost:
          "text-frost hover:bg-surface-soft hover:text-frost",
        link: "text-frost underline-offset-4 hover:underline",
        frost:
          "bg-accent text-accent-foreground shadow-glow hover:bg-accent/90",
      },
      size: {
        default: "h-9 px-4 py-2 has-[>svg]:px-3",
        sm: "h-8 gap-1.5 px-3 has-[>svg]:px-2.5",
        lg: "h-10 px-6 has-[>svg]:px-4",
        xl: "min-h-[52px] px-6 text-base",
        icon: "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
  VariantProps<typeof buttonVariants> {
  asChild?: boolean
  loading?: boolean
}

function LoadingButton({
  className,
  loading = false,
  children,
  disabled,
  variant,
  size,
  asChild = false,
  ...props
}: ButtonProps) {
  const Comp = asChild ? Slot : "button"
  return (
    <Comp
      className={cn(buttonVariants({ variant, size, className }))}
      disabled={loading || disabled}
      {...props}
    >
      {loading && <Loader2 className="mr-2 h-5 w-5 animate-spin" />}
      <Slottable>{children}</Slottable>
    </Comp>
  )
}

export { buttonVariants, LoadingButton }
