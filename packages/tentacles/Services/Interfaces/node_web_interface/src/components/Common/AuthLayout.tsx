import { Logo } from "@/components/Common/Logo"
import { OCTOBOT_WEBSITE_URL } from "@/lib/external-links"

interface AuthLayoutProps {
  children: React.ReactNode
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="min-h-svh flex flex-col items-center justify-center gap-8 p-6 md:p-8">
      <div className="glass-card-hero w-full max-w-sm p-8 flex flex-col gap-8">
        <div className="flex items-center justify-center">
          <Logo variant="full" className="h-10 md:h-12" asLink={false} />
        </div>
        <div>{children}</div>
        <p className="text-center">
          <a
            href={OCTOBOT_WEBSITE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground"
          >
            OctoBot website
          </a>
        </p>
      </div>
    </div>
  )
}
