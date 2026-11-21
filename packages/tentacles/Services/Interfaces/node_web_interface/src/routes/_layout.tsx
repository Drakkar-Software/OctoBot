import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"

import { AppHeader } from "@/components/Common/AppHeader"
import { isLoggedIn } from "@/hooks/useAuth"
import { safeReturnTo } from "@/lib/safe-return-to"

export const Route = createFileRoute("/_layout")({
  component: Layout,
  beforeLoad: async ({ location }) => {
    if (!isLoggedIn()) {
      const returnTo = safeReturnTo(location.pathname)
      throw redirect({
        to: "/login",
        search: returnTo ? { returnTo: location.pathname } : {},
      })
    }
  },
})

function Layout() {
  return (
    <div className="min-h-screen bg-halo bg-fixed text-foreground">
      <AppHeader />
      <main className="px-6 py-8">
        <div className="mx-auto max-w-7xl">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

export default Layout
