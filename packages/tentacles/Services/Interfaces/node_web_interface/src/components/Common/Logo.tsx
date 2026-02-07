import { Link } from "@tanstack/react-router"

import { cn, getAssetPath } from "@/lib/utils"

interface LogoProps {
  variant?: "full" | "icon" | "responsive"
  className?: string
  asLink?: boolean
}

export function Logo({
  variant = "full",
  className,
  asLink = true,
}: LogoProps) {
  const logoPath = getAssetPath("images/octobot_node_1024.png")
  const iconPath = getAssetPath("images/octobot_node_100.png")

  const content =
    variant === "responsive" ? (
      <div className="flex flex-row items-center gap-2">
        <img
          src={logoPath}
          alt="OctoBot Node"
          className={cn(
            "h-6 w-auto group-data-[collapsible=icon]:hidden",
            className,
          )}
        />
        <img
          src={iconPath}
          alt="OctoBot Node"
          className={cn(
            "size-5 hidden group-data-[collapsible=icon]:block",
            className,
          )}
        />
        <span className="hidden lg:block text-lg font-semibold group-data-[collapsible=icon]:hidden">
          OctoBot Node
        </span>
      </div>
    ) : (
      <div className="flex flex-row items-center gap-2">
        <img
          src={variant === "full" ? logoPath : iconPath}
          alt="OctoBot Node"
          className={cn(variant === "full" ? "h-6 w-auto" : "size-5", className)}
        />
        {variant === "full" && (
          <span className="hidden lg:block text-lg font-semibold">
            OctoBot Node
          </span>
        )}
      </div>
    )

  if (!asLink) {
    return content
  }

  return <Link to="/">{content}</Link>
}
