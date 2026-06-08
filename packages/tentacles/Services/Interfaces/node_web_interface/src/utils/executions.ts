import type { Execution, TaskStatus } from "@/client"

export function getStatusGroup(
  status?: TaskStatus | null,
): "active" | "stopped" {
  if (!status) return "active"
  if (
    status === "running" ||
    status === "scheduled" ||
    status === "periodic" ||
    status === "pending"
  ) {
    return "active"
  }
  return "stopped"
}

export function getActiveExecution(
  executions: Execution[] | undefined | null,
): Execution | null {
  if (!executions?.length) return null
  const pending = executions.filter((e) => e.status === "pending")
  if (pending.length) return pending[pending.length - 1]
  const dated = [...executions]
    .filter((e) => e.completed_at != null)
    .sort(
      (a, b) =>
        new Date(b.completed_at!).getTime() -
        new Date(a.completed_at!).getTime(),
    )
  return dated[0] ?? executions[executions.length - 1]
}

export function hasStartedExecution(
  executions: Execution[] | null | undefined,
): boolean {
  return !!executions?.some(
    (e) => e.status === "running" || e.completed_at != null,
  )
}
