import { Link } from "@tanstack/react-router"
import { LogOut, Settings, Sliders, Users2 } from "lucide-react"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import useAuth from "@/hooks/useAuth"
import { getInitials } from "@/utils"

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
          <Avatar className="size-7">
            <AvatarFallback className="bg-zinc-600 text-white text-xs">
              {getInitials(user?.full_name || "User")}
            </AvatarFallback>
          </Avatar>
          <span className="hidden sm:block">{user?.full_name || "Admin"}</span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-64" align="end" sideOffset={8}>
        <DropdownMenuLabel className="flex flex-col gap-1">
          <span className="text-sm font-medium">{user?.full_name || "Admin"}</span>
          <span className="text-xs text-muted-foreground">{user?.email}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
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
