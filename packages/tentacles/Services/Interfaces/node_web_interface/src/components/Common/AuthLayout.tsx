import { Logo } from "@/components/Common/Logo"
import { cn } from "@/lib/utils"

interface AuthLayoutProps {
  children: React.ReactNode
  wide?: boolean
}

export function AuthLayout({ children, wide = false }: AuthLayoutProps) {
  return (
    <div className="min-h-svh flex flex-col items-center justify-center gap-8 p-6 md:p-8">
      <div
        className={cn(
          "glass-card-hero w-full p-8 flex flex-col gap-8",
          wide ? "max-w-xl" : "max-w-sm",
        )}
      >
        <div className="flex items-center justify-center">
          <Logo variant="full" className="h-10 md:h-12" asLink={false} />
        </div>
        <div>{children}</div>
      </div>
    </div>
  )
}
