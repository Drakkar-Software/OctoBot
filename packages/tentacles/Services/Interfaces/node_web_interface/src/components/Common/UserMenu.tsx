import { useMemo } from "react"
import { Link } from "@tanstack/react-router"
import { ShieldCheck, User } from "lucide-react"

import useAuth from "@/hooks/useAuth"

function displayName(email: string | undefined, fullName: string | null | undefined): string {
  // Prefer server-sourced name (user.full_name) to avoid showing stale localStorage value
  if (fullName) return fullName
  const stored = localStorage.getItem("auth_wallet_name")
  if (stored) return stored
  if (!email) return "—"
  return email.length > 12 ? `${email.slice(0, 6)}…${email.slice(-4)}` : email
}

export function UserMenu() {
  const { user } = useAuth()
  const name = useMemo(() => displayName(user?.email, user?.full_name), [user?.email, user?.full_name])

  if (!user) return null

  return (
    <div className="flex items-center gap-2">
      <Link
        to="/settings"
        className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium hover:bg-accent transition-colors"
        data-testid="user-menu"
      >
        <span className="flex size-7 items-center justify-center rounded-full bg-zinc-600 text-white">
          <User className="size-4" />
        </span>
        <span className="hidden sm:flex items-center gap-1.5">
          {name}
          {user.is_superuser && (
            <ShieldCheck className="size-3.5 text-primary" />
          )}
        </span>
      </Link>
    </div>
  )
}

export default UserMenu
