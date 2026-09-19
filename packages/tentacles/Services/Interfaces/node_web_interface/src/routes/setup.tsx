import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"
import { SetupService } from "@/client"
import { isLoggedIn } from "@/hooks/useAuth"
import {
  getSetupRedirect,
  START_FRESH_FROM_RECOVER_KEY,
} from "@/lib/setup-guard"

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
      startFreshFromRecover:
        sessionStorage.getItem(START_FRESH_FROM_RECOVER_KEY) === "1",
    })
    if (target) throw redirect({ to: target })
  },
  component: () => <Outlet />,
  head: () => ({
    meta: [{ title: "Setup" }],
  }),
})
