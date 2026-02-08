import { createFileRoute, redirect } from "@tanstack/react-router"

export const Route = createFileRoute("/_layout/")({
  beforeLoad: () => {
    throw redirect({
      to: "/octobots",
    })
  },
})
