import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { Suspense, useMemo } from "react"

import ExportResultsContent from "@/components/Tasks/ExportResultsContent"
import { getTasksQueryOptions } from "@/lib/task-queries"
import { getActiveExecution, getStatusGroup } from "@/utils/executions"

interface ExportSearchParams {
  tasks: string
}

export const Route = createFileRoute("/_layout/octobots/export")({
  component: ExportOctobots,
  validateSearch: (search: Record<string, unknown>): ExportSearchParams => ({
    tasks: typeof search.tasks === "string" ? search.tasks : "",
  }),
  head: () => ({
    meta: [{ title: "Export Results" }],
  }),
})

function ExportContent({ taskIds }: { taskIds: string[] }) {
  const navigate = useNavigate()
  const { data: allTasks } = useSuspenseQuery(getTasksQueryOptions())

  const exportTasks = useMemo(
    () =>
      allTasks.filter(
        (t) =>
          t.id &&
          taskIds.includes(t.id) &&
          getStatusGroup(getActiveExecution(t.executions)?.status) === "stopped",
      ),
    [allTasks, taskIds],
  )

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Export Results</h1>
        <p className="text-muted-foreground">
          Select a template, review the data, and export as CSV.
        </p>
      </div>
      <ExportResultsContent
        tasks={exportTasks}
        onClose={() => navigate({ to: "/octobots" })}
      />
    </div>
  )
}

function ExportOctobots() {
  const { tasks: tasksParam } = Route.useSearch()
  const taskIds = useMemo(
    () => tasksParam.split(",").filter(Boolean),
    [tasksParam],
  )

  return (
    <Suspense fallback={<div className="text-muted-foreground">Loading export data...</div>}>
      <ExportContent taskIds={taskIds} />
    </Suspense>
  )
}
