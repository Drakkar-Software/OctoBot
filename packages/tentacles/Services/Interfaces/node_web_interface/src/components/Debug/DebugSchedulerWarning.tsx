import { TriangleAlert } from "lucide-react"

export function DebugSchedulerWarning() {
  return (
    <div className="flex items-start gap-2 rounded-md border border-warn/30 bg-warn/10 p-4 text-sm text-warn">
      <TriangleAlert className="mt-0.5 size-4 shrink-0" />
      <span>
        Scheduler is not initialized. Debug data is unavailable until the node
        scheduler has started.
      </span>
    </div>
  )
}
