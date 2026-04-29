import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"
import { isLoggedIn } from "@/hooks/useAuth"
import { SetupService } from "@/client"

export const Route = createFileRoute("/setup")({
  beforeLoad: async () => {
    let configured = false
    try {
      const status = await SetupService.getSetupStatus()
      configured = status.configured
    } catch {
      // network error — stay on setup
    }
    if (configured && !sessionStorage.getItem("setup_in_progress")) {
      throw redirect({ to: isLoggedIn() ? "/" : "/login" })
    }
  },
  component: () => <Outlet />,
  head: () => ({
    meta: [{ title: "Setup" }],
  }),
})
