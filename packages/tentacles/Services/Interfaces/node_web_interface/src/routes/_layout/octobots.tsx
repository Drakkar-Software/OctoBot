import { createFileRoute, Outlet } from "@tanstack/react-router"

export const Route = createFileRoute("/_layout/octobots")({
  component: Octobots,
})

function Octobots() {
  return <Outlet />
}
