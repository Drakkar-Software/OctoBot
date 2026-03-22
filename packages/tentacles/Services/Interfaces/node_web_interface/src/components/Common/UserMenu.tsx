import { Link } from "@tanstack/react-router"
import { LogOut, Settings, User } from "lucide-react"

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import useAuth from "@/hooks/useAuth"

export function UserMenu() {
  const { user, logout } = useAuth()

  if (!user) return null

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium"
          data-testid="user-menu"
        >
          <span className="flex size-7 items-center justify-center rounded-full bg-zinc-600 text-white">
            <User className="size-4" />
          </span>
          <span className="hidden sm:block">{user?.full_name || user?.email?.slice(0, 8) || "—"}</span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-64" align="end" sideOffset={8}>
        {/* <DropdownMenuItem asChild>
          <Link to="/tentacles">
            <Sliders className="size-4" />
            Manage tentacles
          </Link>
        </DropdownMenuItem> */}
        {/* <DropdownMenuSeparator /> */}
        <DropdownMenuItem asChild>
          <Link to="/settings">
            <Settings className="size-4" />
            Settings
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem onClick={logout}>
          <LogOut className="size-4" />
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export default UserMenu
