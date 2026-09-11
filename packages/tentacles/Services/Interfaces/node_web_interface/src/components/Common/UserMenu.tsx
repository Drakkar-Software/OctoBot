import { Link } from "@tanstack/react-router"
import { ShieldCheck, User } from "lucide-react"
import type { ReactNode } from "react"
import { useMemo } from "react"

import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import {
  displayName,
  getCachedNavbarDisplayName,
  getStoredIsSuperuser,
} from "@/lib/user-menu-display"

type UserMenuShellProps = {
  children: ReactNode
}

function UserMenuShell({ children }: UserMenuShellProps) {
  return (
    <div className="flex items-center gap-2">
      <Link
        to="/settings"
        className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium hover:bg-surface-strong transition-colors"
        data-testid="user-menu"
      >
        <span className="flex size-7 items-center justify-center rounded-full bg-surface-strong text-frost">
          <User className="size-4" />
        </span>
        <span className="hidden sm:flex items-center gap-1.5">{children}</span>
      </Link>
    </div>
  )
}

export function UserMenu() {
  const { user, isCurrentUserPending } = useAuth()
  const name = useMemo(
    () =>
      user
        ? displayName(user.email, user.full_name)
        : getCachedNavbarDisplayName(),
    [user?.email, user?.full_name, user],
  )
  const showSuperuserBadge = user
    ? user.is_superuser === true
    : getStoredIsSuperuser()

  if (!isLoggedIn()) {
    return null
  }

  if (!isCurrentUserPending && !user) {
    return null
  }

  return (
    <UserMenuShell>
      {name}
      {showSuperuserBadge && <ShieldCheck className="size-3.5 text-primary" />}
    </UserMenuShell>
  )
}

export default UserMenu
