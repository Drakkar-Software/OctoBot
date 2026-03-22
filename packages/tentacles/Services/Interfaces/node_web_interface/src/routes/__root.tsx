import { ReactQueryDevtools } from "@tanstack/react-query-devtools"
import { createRootRoute, HeadContent, Outlet, redirect } from "@tanstack/react-router"
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools"
import ErrorComponent from "@/components/Common/ErrorComponent"
import NotFound from "@/components/Common/NotFound"
import { SetupService } from "@/client"

export const Route = createRootRoute({
  beforeLoad: async ({ location }) => {
    let configured = true
    try {
      const status = await SetupService.getSetupStatus()
      configured = status.configured
    } catch {
      // network error — do not block navigation
    }
    if (!configured && !location.pathname.startsWith("/setup")) {
      throw redirect({ to: "/setup" })
    }
  },
  component: () => (
    <>
      <HeadContent />
      <Outlet />
      <TanStackRouterDevtools position="bottom-right" />
      <ReactQueryDevtools initialIsOpen={false} />
    </>
  ),
  notFoundComponent: () => <NotFound />,
  errorComponent: () => <ErrorComponent />,
})
