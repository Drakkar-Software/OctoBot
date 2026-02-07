import { createFileRoute } from "@tanstack/react-router"

import NodeCard from "@/components/Nodes/NodeCard"
import { Logs } from "@/components/System/Logs"

export const Route = createFileRoute("/_layout/system")({
  component: System,
  head: () => ({
    meta: [
      {
        title: "System",
      },
    ],
  }),
})

function System() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">System</h1>
          <p className="text-muted-foreground">Node status and system logs</p>
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <NodeCard />
        <Logs />
      </div>
    </div>
  )
}
