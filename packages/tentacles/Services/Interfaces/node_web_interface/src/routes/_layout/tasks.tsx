import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Search } from "lucide-react"
import { Suspense, useState } from "react"

import type { TaskStatus } from "@/client"
import { TasksService } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import ImportTask from "@/components/Tasks/ImportTask"
import ExportResults from "@/components/Tasks/ExportResults"
import { columns } from "@/components/Tasks/columns"
import PendingTasks from "@/components/Tasks/PendingTasks"
import { TaskMetrics } from "@/components/Tasks/TaskMetrics"

function getTasksQueryOptions() {
  return {
    queryFn: () => TasksService.getTasks({ page: 1, limit: 100 }),
    queryKey: ["tasks"],
  }
}

export const Route = createFileRoute("/_layout/tasks")({
  component: Tasks,
  head: () => ({
    meta: [
      {
        title: "Tasks",
      },
    ],
  }),
})

interface TasksTableContentProps {
  filter?: TaskStatus | null
}

function TasksTableContent({ filter }: TasksTableContentProps) {
  const { data: tasks } = useSuspenseQuery(getTasksQueryOptions())

  const filteredTasks = filter
    ? tasks.filter((task) => {
        // When filtering by "scheduled", include both scheduled and periodic tasks
        if (filter === "scheduled") {
          return task.status === "scheduled" || task.status === "periodic"
        }
        return task.status === filter
      })
    : tasks

  if (tasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Search className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">You don't have any tasks yet</h3>
        <p className="text-muted-foreground">Create or import a task to get started</p>
      </div>
    )
  }

  if (filteredTasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Search className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">No tasks found</h3>
        <p className="text-muted-foreground">No tasks match the selected filter</p>
      </div>
    )
  }

  return <DataTable columns={columns} data={filteredTasks} />
}

interface TasksTableProps {
  filter?: TaskStatus | null
}

function TasksTable({ filter }: TasksTableProps) {
  return (
    <Suspense fallback={<PendingTasks />}>
      <TasksTableContent filter={filter} />
    </Suspense>
  )
}

function Tasks() {
  const [selectedFilter, setSelectedFilter] = useState<TaskStatus | null>(null)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Tasks</h1>
          <p className="text-muted-foreground">Create and manage your tasks</p>
        </div>
        <div className="flex gap-2">
          <ImportTask />
          <ExportResults />
          {/* <AddTask /> */}
        </div>
      </div>
      <TaskMetrics 
        selectedFilter={selectedFilter} 
        onFilterChange={setSelectedFilter} 
      />
      <TasksTable filter={selectedFilter} />
    </div>
  )
}

