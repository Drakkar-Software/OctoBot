import { Logo } from "@/components/Common/Logo"

interface AuthLayoutProps {
  children: React.ReactNode
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="min-h-svh flex flex-col items-center justify-center gap-8 p-6 md:p-8">
      <div className="flex items-center justify-center">
        <Logo variant="full" className="h-12 md:h-16" asLink={false} />
      </div>
      <div className="w-full max-w-sm">{children}</div>
    </div>
  )
}
