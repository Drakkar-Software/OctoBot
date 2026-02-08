import { Logo } from "@/components/Common/Logo"
import UserMenu from "@/components/Common/UserMenu"

export function AppHeader() {
  return (
    <header className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-4 px-6 py-4">
        <Logo variant="full" />
        <div className="ml-auto flex items-center gap-2">
          <UserMenu />
        </div>
      </div>
    </header>
  )
}

export default AppHeader
