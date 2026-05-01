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

export type BadgeVariant =
  | "default"
  | "secondary"
  | "destructive"
  | "outline"
  | "pos"
  | "neg"
  | "warn"
  | "frost"

export function getStatusVariant(
  status?: TaskStatus | null,
  hasError?: boolean,
): BadgeVariant {
  if (hasError) return "neg"
  if (!status) return "secondary"
  if (status === "running") return "frost"
  if (status === "failed") return "neg"
  if (status === "completed") return "pos"
  if (status === "scheduled" || status === "pending" || status === "periodic")
    return "warn"
  return "secondary"
}

export function getTaskFilterGroup(task: Task): TaskFilterGroup {
  const exec = getActiveExecution(task.executions)
  if (getStatusGroup(exec?.status) === "active") return "active"
  return exec?.status === "failed" || exec?.error ? "errored" : "completed"
}

export function getTaskSortDate(task: Task): string | null {
  const exec = getActiveExecution(task.executions)
  return (exec?.completed_at ?? exec?.scheduled_at) as string | null
}

export function getDisplayDate(
  task: Task,
): { label: string; value: string } | null {
  const exec = getActiveExecution(task.executions)
  if (exec?.completed_at) return { label: "Last run", value: exec.completed_at }
  if (exec?.scheduled_at) return { label: "Next run", value: exec.scheduled_at }
  return null
}
