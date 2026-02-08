import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { Bot, Download, Plus } from "lucide-react"
import { Suspense, useMemo, useState } from "react"

import type { Task, TaskStatus } from "@/client"
import { TasksService } from "@/client"
import { CollectionHeader } from "@/components/Common/CollectionHeader"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

function getTasksQueryOptions() {
  return {
    queryFn: () => TasksService.getTasks({ page: 1, limit: 100 }),
    queryKey: ["tasks"],
  }
}

const filters = [
  { value: "all", label: "All" },
  { value: "running", label: "Running" },
  { value: "scheduled", label: "Scheduled" },
  { value: "stopped", label: "Stopped" },
  { value: "terminated", label: "Terminated" },
]

const statusLabels: Record<TaskStatus, string> = {
  pending: "Pending",
  scheduled: "Scheduled",
  periodic: "Recurring",
  running: "Running",
  completed: "Stopped",
  failed: "Terminated",
}

function getStatusVariant(status?: TaskStatus | null) {
  if (!status) return "secondary" as const
  if (status === "running") return "default" as const
  if (status === "failed") return "destructive" as const
  if (status === "completed") return "outline" as const
  return "secondary" as const
}

function getStatusGroup(status?: TaskStatus | null) {
  if (!status) return "scheduled"
  if (status === "running") return "running"
  if (status === "scheduled" || status === "periodic" || status === "pending") {
    return "scheduled"
  }
  if (status === "failed") return "terminated"
  return "stopped"
}

function getDisplayDate(task: Task) {
  if (task.started_at) return { label: "Started", value: task.started_at }
  if (task.scheduled_at) return { label: "Scheduled", value: task.scheduled_at }
  if (task.completed_at) return { label: "Stopped", value: task.completed_at }
  return { label: "Created", value: "—" }
}

function OctobotCard({ task }: { task: Task }) {
  const label = task.name || `OctoBot ${task.id?.slice(0, 6) || "new"}`
  const status = task.status || "scheduled"
  const date = getDisplayDate(task)

  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardHeader className="gap-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-xl bg-muted">
              <Bot className="size-5 text-muted-foreground" />
            </div>
            <div>
              <CardTitle>{label}</CardTitle>
              <CardDescription className="text-xs">
                {task.type || "Strategy"} · {task.description || "No description"}
              </CardDescription>
            </div>
          </div>
          <Badge variant={getStatusVariant(status)}>{statusLabels[status]}</Badge>
        </div>
      </CardHeader>
      <CardContent className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {date.label}: {date.value}
        </span>
        <span>ID: {task.id?.slice(0, 8) || "—"}</span>
      </CardContent>
    </Card>
  )
}

function OctobotGrid({
  tasks,
  filter,
  search,
}: {
  tasks: Task[]
  filter: string
  search: string
}) {
  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    return tasks.filter((task) => {
      const inFilter =
        filter === "all" ? true : getStatusGroup(task.status) === filter
      const inSearch = query
        ? `${task.name ?? ""} ${task.description ?? ""} ${task.type ?? ""}`
            .toLowerCase()
            .includes(query)
        : true
      return inFilter && inSearch
    })
  }, [tasks, filter, search])

  if (tasks.length === 0) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle>No OctoBots yet</CardTitle>
          <CardDescription>
            Start your first OctoBot or import a saved configuration.
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  if (filtered.length === 0) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle>No OctoBots match this filter</CardTitle>
          <CardDescription>Try another filter or search term.</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {filtered.map((task) => (
        <OctobotCard key={task.id} task={task} />
      ))}
    </div>
  )
}

function OctobotsContent() {
  const { data: tasks } = useSuspenseQuery(getTasksQueryOptions())
  const [filterValue, setFilterValue] = useState("all")
  const [searchValue, setSearchValue] = useState("")
  const counts = useMemo(() => {
    return {
      all: tasks.length,
      running: tasks.filter((task) => getStatusGroup(task.status) === "running")
        .length,
      scheduled: tasks.filter(
        (task) => getStatusGroup(task.status) === "scheduled"
      ).length,
      stopped: tasks.filter((task) => getStatusGroup(task.status) === "stopped")
        .length,
      terminated: tasks.filter(
        (task) => getStatusGroup(task.status) === "terminated"
      ).length,
    }
  }, [tasks])

  return (
    <div className="flex flex-col gap-8">
      <CollectionHeader
        title="OctoBots"
        description="Monitor running, scheduled, and stopped OctoBots."
        action={
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline" size="lg">
              <Link to="/octobots/import">
                <Download className="size-4" />
                Import OctoBots
              </Link>
            </Button>
            <Button asChild size="lg">
              <Link to="/octobots/new">
                <Plus className="size-4" />
                Start new OctoBot
              </Link>
            </Button>
          </div>
        }
        searchValue={searchValue}
        onSearchChange={setSearchValue}
        searchPlaceholder="Search OctoBots..."
        filters={filters.map((filter) => ({
          ...filter,
          label: `${filter.label} (${counts[filter.value as keyof typeof counts]})`,
        }))}
        filterValue={filterValue}
        onFilterChange={setFilterValue}
      />
      <OctobotGrid tasks={tasks} filter={filterValue} search={searchValue} />
    </div>
  )
}

export const Route = createFileRoute("/_layout/octobots")({
  component: Octobots,
  head: () => ({
    meta: [{ title: "OctoBots" }],
  }),
})

function Octobots() {
  return (
    <Suspense fallback={<div>Loading OctoBots...</div>}>
      <OctobotsContent />
    </Suspense>
  )
}
