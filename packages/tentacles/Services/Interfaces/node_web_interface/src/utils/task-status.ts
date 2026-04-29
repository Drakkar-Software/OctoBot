import type { Task_Output as Task, TaskStatus } from "@/client"
import { getActiveExecution, getStatusGroup } from "@/utils/executions"

export type TaskFilterGroup = "active" | "completed" | "errored"

export const filters: { value: TaskFilterGroup; label: string }[] = [
  { value: "active", label: "Active" },
  { value: "completed", label: "Completed" },
  { value: "errored", label: "Errored" },
]

export const statusLabels: Record<TaskStatus, string> = {
  pending: "Pending",
  scheduled: "Scheduled",
  periodic: "Recurring",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
}

export function getStatusVariant(status?: TaskStatus | null, hasError?: boolean) {
  if (hasError) return "destructive" as const
  if (!status) return "secondary" as const
  if (status === "running") return "default" as const
  if (status === "failed") return "destructive" as const
  if (status === "completed") return "outline" as const
  return "secondary" as const
}

export function getTaskFilterGroup(task: Task): TaskFilterGroup {
  const status = getActiveExecution(task.executions)?.status
  if (getStatusGroup(status) === "active") return "active"
  return task.error ? "errored" : "completed"
}

export function getTaskSortDate(task: Task): string | null {
  const exec = getActiveExecution(task.executions)
  return (exec?.completed_at ?? exec?.scheduled_at) as string | null
}

export function getDisplayDate(task: Task): { label: string; value: string } | null {
  const exec = getActiveExecution(task.executions)
  if (exec?.completed_at) return { label: "Last run", value: exec.completed_at }
  if (exec?.scheduled_at) return { label: "Next run", value: exec.scheduled_at }
  return null
}
