import { Link } from "@tanstack/react-router"
import { User } from "lucide-react"

import useAuth from "@/hooks/useAuth"

export function UserMenu() {
  const { user } = useAuth()

  if (!user) return null

  return (
    <Link
      to="/settings"
      className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium hover:bg-accent transition-colors"
      data-testid="user-menu"
    >
      <span className="flex size-7 items-center justify-center rounded-full bg-zinc-600 text-white">
        <User className="size-4" />
      </span>
      <span className="hidden sm:block">{user?.full_name || user?.email?.slice(0, 8) || "—"}</span>
    </Link>
  )
}

export default UserMenu
