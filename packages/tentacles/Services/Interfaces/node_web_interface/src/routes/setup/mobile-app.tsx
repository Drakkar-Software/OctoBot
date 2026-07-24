import { createFileRoute, redirect } from "@tanstack/react-router"

export const Route = createFileRoute("/setup/mobile-app")({
  beforeLoad: () => {
    throw redirect({ to: "/setup/connect" })
  },
})
