import { createFileRoute } from "@tanstack/react-router"

import { DebugView } from "@/components/Debug/DebugView"

function DebugPage() {
  return <DebugView />
}

export const Route = createFileRoute("/_layout/debug")({
  component: DebugPage,
  head: () => ({
    meta: [{ title: "Debug view" }],
  }),
})
