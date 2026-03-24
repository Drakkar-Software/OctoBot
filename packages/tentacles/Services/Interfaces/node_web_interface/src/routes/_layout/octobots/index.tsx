import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { Bot, Check, Clock, Layers, Plus, Trash2 } from "lucide-react"
import { Suspense, useMemo, useState } from "react"

import type { Task_Output as Task, TaskStatus } from "@/client"
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
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { generateCSV, downloadCSV } from "@/lib/csv"
import { cn } from "@/lib/utils"
import { getActiveExecution } from "@/utils/executions"

function getTasksQueryOptions() {
  return {
    queryFn: () => TasksService.getTasks({ page: 1, limit: 100 }),
    queryKey: ["tasks"],
    refetchInterval: 5_000,
  }
}

const filters = [
  { value: "all", label: "All" },
  { value: "running", label: "Running" },
  { value: "scheduled", label: "Scheduled" },
  { value: "stopped", label: "Stopped" },
]

const statusLabels: Record<TaskStatus, string> = {
  pending: "Pending",
  scheduled: "Scheduled",
  periodic: "Recurring",
  running: "Running",
  completed: "Stopped",
  failed: "Failed",
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
  return "stopped"
}

function getDisplayDate(task: Task) {
  const completed_at = getActiveExecution(task.executions)?.completed_at
  if (completed_at) return { label: "Executed at", value: completed_at }
  return { label: "Created", value: "—" }
}


function formatDate(value: string | null | undefined): string {
  if (!value || value === "—") return "—"
  try {
    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value))
  } catch {
    return value
  }
}

function BotCardBody({ task }: { task: Task }) {
  const activeExec = getActiveExecution(task.executions)
  const group = getStatusGroup(activeExec?.status)
  const date = getDisplayDate(task)
  const stepCount = task.executions?.length ?? 0
  const pendingSteps = task.executions?.filter((e) => e.status === "pending").length ?? 0
  const completedSteps = task.executions?.filter((e) => e.status === "completed" || e.status === "failed").length ?? 0

  if (group === "running") {
    return (
      <CardContent className="flex flex-col gap-2 pt-0">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          {completedSteps > 0 && (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <Layers className="size-3.5" />
              {completedSteps} done
            </span>
          )}
          {pendingSteps > 0 && (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="size-3.5" />
              {pendingSteps} remaining
            </span>
          )}
        </div>
        <div className="text-xs text-muted-foreground">
          {date.label}: {formatDate(date.value as string)}
        </div>
      </CardContent>
    )
  }

  if (group === "scheduled") {
    return (
      <CardContent className="flex flex-col gap-2 pt-0">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          {activeExec?.type && (
            <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
              {activeExec.type}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Clock className="size-3.5 shrink-0" />
          {date.label}: {formatDate(date.value as string)}
        </div>
      </CardContent>
    )
  }

  const isFailed = activeExec?.status === "failed"

  return (
    <CardContent className="flex flex-col gap-2 pt-0">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {activeExec?.type && (
          <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
            {activeExec.type}
          </span>
        )}
        {stepCount > 0 && (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Layers className="size-3.5" />
            {stepCount} step{stepCount !== 1 ? "s" : ""}
          </span>
        )}
      </div>
      <div className={cn("text-xs", isFailed ? "text-destructive/80" : "text-muted-foreground")}>
        {date.label}: {formatDate(date.value as string)}
      </div>
    </CardContent>
  )
}

function BotCard({
  task,
  selected,
  onToggleSelect,
}: {
  task: Task
  selected: boolean
  onToggleSelect: (id: string) => void
}) {
  const label = task.name || `OctoBot ${task.id?.slice(0, 6) || "new"}`
  const status = (getActiveExecution(task.executions)?.status || "scheduled") as TaskStatus

  return (
    <Card
      className={cn(
        "relative cursor-pointer transition-all hover:shadow-md",
        selected
          ? "ring-2 ring-primary shadow-md"
          : "hover:ring-1 hover:ring-primary/40",
      )}
      onClick={() => task.id && onToggleSelect(task.id)}
    >
      {selected && (
        <div className="absolute right-3 top-3 flex size-5 items-center justify-center rounded-full bg-primary">
          <Check className="size-3 text-primary-foreground" />
        </div>
      )}
      <CardHeader className="gap-1.5 pb-3">
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-muted">
            <Bot className="size-5 text-muted-foreground" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="grid grid-cols-[1fr_auto] items-start gap-2">
              <span className="truncate text-sm font-semibold leading-tight">{label}</span>
              <Badge variant={getStatusVariant(status)} className={cn(selected && "mr-6")}>
                {statusLabels[status]}
              </Badge>
            </div>
            <span className="mt-0.5 block font-mono text-xs text-muted-foreground">
              ID: {task.id?.slice(0, 12) || "—"}
            </span>
          </div>
        </div>
      </CardHeader>
      <BotCardBody task={task} />
    </Card>
  )
}

function BotGrid({
  tasks,
  filter,
  search,
  selectedIds,
  onToggleSelect,
}: {
  tasks: Task[]
  filter: string
  search: string
  selectedIds: Set<string>
  onToggleSelect: (id: string) => void
}) {
  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    return tasks.filter((task) => {
      const activeExec = getActiveExecution(task.executions)
      const inFilter =
        filter === "all" ? true : getStatusGroup(activeExec?.status) === filter
      const inSearch = query
        ? `${task.name ?? ""} ${activeExec?.type ?? ""}`
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
        <BotCard
          key={task.id}
          task={task}
          selected={task.id ? selectedIds.has(task.id) : false}
          onToggleSelect={onToggleSelect}
        />
      ))}
    </div>
  )
}

function SelectionToolbar({
  selectedIds,
  filteredTasks,
  allTasks,
  onSelectAll,
  onDeselectAll,
  onDeleted,
}: {
  selectedIds: Set<string>
  filteredTasks: Task[]
  allTasks: Task[]
  onSelectAll: () => void
  onDeselectAll: () => void
  onDeleted: () => void
}) {
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [shareLogsOpen, setShareLogsOpen] = useState(false)
  const [shareLogsLoading, setShareLogsLoading] = useState(false)
  const [shareCreds, setShareCreds] = useState<{ errorId: string; errorSecret: string } | null>(null)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const deleteMutation = useMutation({
    mutationFn: async () => {
      for (const id of selectedIds) {
        await TasksService.deleteTask({ taskId: id })
      }
    },
    onSuccess: () => {
      showSuccessToast(`Deleted ${selectedIds.size} OctoBot${selectedIds.size !== 1 ? "s" : ""}`)
      setDeleteOpen(false)
      onDeleted()
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
    },
    onError: () => {
      showErrorToast("Some deletions failed")
    },
  })

  const handleExportResults = () => {
    const selected = allTasks.filter(
      (t) => t.id && selectedIds.has(t.id) && getStatusGroup(getActiveExecution(t.executions)?.status) === "stopped"
    )
    if (selected.length === 0) {
      showErrorToast("No results to export for selected OctoBots")
      return
    }
    const headers = ["name", "status", "result", "result_metadata"]
    const rows = selected.map((t) => {
      const activeExec = getActiveExecution(t.executions)
      let resultValue = activeExec?.result
      try {
        const parsed = activeExec?.result ? JSON.parse(activeExec.result) : null
        resultValue = parsed !== null ? JSON.stringify(parsed) : activeExec?.result
      } catch { /* raw string */ }
      return [t.name || "", activeExec?.status || "", resultValue || "", activeExec?.result_metadata || ""]
    })
    const csv = generateCSV(headers, rows)
    downloadCSV(csv, `task-results-${new Date().toISOString().split("T")[0]}`)
    showSuccessToast(`Exported ${selected.length} result${selected.length !== 1 ? "s" : ""}`)
  }

  const handleShareLogs = async () => {
    setShareLogsLoading(true)
    try {
      const username = localStorage.getItem("auth_username") || "node"
      const password = localStorage.getItem("auth_password") || ""
      const res = await fetch("/api/v1/logs/share", {
        method: "POST",
        headers: {
          Authorization: `Basic ${btoa(`${username}:${password}`)}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ automation_ids: Array.from(selectedIds) }),
      })
      const data = await res.json()
      if (data.success) {
        setShareCreds({ errorId: data.errorId, errorSecret: data.errorSecret })
        setShareLogsOpen(true)
      } else {
        showErrorToast(data.error ?? "Failed to share logs")
      }
    } catch {
      showErrorToast("Failed to share logs")
    } finally {
      setShareLogsLoading(false)
    }
  }

  const allFilteredSelected = filteredTasks.every((t) => t.id && selectedIds.has(t.id))

  return (
    <>
      <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-muted/50 px-4 py-2 text-sm">
        <span className="font-medium">{selectedIds.size} selected</span>
        <div className="flex gap-2">
          {!allFilteredSelected && (
            <Button variant="ghost" size="sm" onClick={onSelectAll}>
              Select all
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={onDeselectAll}>
            Deselect all
          </Button>
        </div>
        <div className="ml-auto flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={handleExportResults}>
            Export results
          </Button>
          <LoadingButton variant="outline" size="sm" loading={shareLogsLoading} onClick={handleShareLogs}>
            Share logs
          </LoadingButton>
          <Button variant="destructive" size="sm" onClick={() => setDeleteOpen(true)}>
            <Trash2 className="size-3.5" />
            Delete
          </Button>
        </div>
      </div>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete {selectedIds.size} OctoBot{selectedIds.size !== 1 ? "s" : ""}</DialogTitle>
            <DialogDescription>
              This will permanently delete the selected OctoBots. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4">
            <DialogClose asChild>
              <Button variant="outline" disabled={deleteMutation.isPending}>Cancel</Button>
            </DialogClose>
            <LoadingButton
              variant="destructive"
              loading={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
            >
              Delete
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={shareLogsOpen} onOpenChange={setShareLogsOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Logs shared</DialogTitle>
            <DialogDescription>
              Share these credentials with the OctoBot team to help diagnose issues.
            </DialogDescription>
          </DialogHeader>
          {shareCreds && (
            <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
              <span className="font-medium text-muted-foreground">Error ID</span>
              <span className="select-all break-all font-mono text-xs">{shareCreds.errorId}</span>
              <span className="font-medium text-muted-foreground">Error Secret</span>
              <span className="select-all break-all font-mono text-xs">{shareCreds.errorSecret}</span>
            </div>
          )}
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Close</Button>
            </DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}


function BotsContent() {
  const { data: tasks } = useSuspenseQuery(getTasksQueryOptions())
  const [filterValue, setFilterValue] = useState("all")
  const [searchValue, setSearchValue] = useState("")
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  const filteredTasks = useMemo(() => {
    const query = searchValue.trim().toLowerCase()
    return tasks.filter((task) => {
      const activeExec = getActiveExecution(task.executions)
      const inFilter =
        filterValue === "all" ? true : getStatusGroup(activeExec?.status) === filterValue
      const inSearch = query
        ? `${task.name ?? ""} ${activeExec?.type ?? ""}`
            .toLowerCase()
            .includes(query)
        : true
      return inFilter && inSearch
    })
  }, [tasks, filterValue, searchValue])

  const counts = useMemo(() => {
    return {
      all: tasks.length,
      running: tasks.filter((task) => getStatusGroup(getActiveExecution(task.executions)?.status) === "running").length,
      scheduled: tasks.filter((task) => getStatusGroup(getActiveExecution(task.executions)?.status) === "scheduled").length,
      stopped: tasks.filter((task) => getStatusGroup(getActiveExecution(task.executions)?.status) === "stopped").length,
    }
  }, [tasks])

  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleSelectAll = () => {
    setSelectedIds(new Set(filteredTasks.map((t) => t.id!).filter(Boolean)))
  }

  const handleDeselectAll = () => {
    setSelectedIds(new Set())
  }

  return (
    <div className="flex flex-col gap-8">
      <CollectionHeader
        title="OctoBots"
        description="Monitor running, scheduled, and stopped OctoBots."
        action={
          <Button asChild size="lg">
            <Link to="/octobots/new">
              <Plus className="size-4" />
              New OctoBot
            </Link>
          </Button>
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
      {selectedIds.size > 0 && (
        <SelectionToolbar
          selectedIds={selectedIds}
          filteredTasks={filteredTasks}
          allTasks={tasks}
          onSelectAll={handleSelectAll}
          onDeselectAll={handleDeselectAll}
          onDeleted={handleDeselectAll}
        />
      )}
      <BotGrid
        tasks={tasks}
        filter={filterValue}
        search={searchValue}
        selectedIds={selectedIds}
        onToggleSelect={handleToggleSelect}
      />
    </div>
  )
}

export const Route = createFileRoute("/_layout/octobots/")({
  component: BotsIndex,
  head: () => ({
    meta: [{ title: "OctoBots" }],
  }),
})

function BotsIndex() {
  return (
    <Suspense fallback={<div>Loading OctoBots...</div>}>
      <BotsContent />
    </Suspense>
  )
}
