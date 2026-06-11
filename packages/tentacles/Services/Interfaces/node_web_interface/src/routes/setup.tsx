import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"
import { SetupService } from "@/client"
import { isLoggedIn } from "@/hooks/useAuth"
import { getSetupRedirect } from "@/lib/setup-guard"

export const Route = createFileRoute("/setup")({
  beforeLoad: async ({ location }) => {
    let configured = false
    try {
      configured = (await SetupService.getSetupStatus()).configured
    } catch {
      // network error — stay on setup
    }
    const target = getSetupRedirect({
      configured,
      setupInProgress: !!sessionStorage.getItem("setup_in_progress"),
      loggedIn: isLoggedIn(),
      pathname: location.pathname,
    })
    if (target) throw redirect({ to: target })
  },
  component: () => <Outlet />,
  head: () => ({
    meta: [{ title: "Setup" }],
  }),
})
