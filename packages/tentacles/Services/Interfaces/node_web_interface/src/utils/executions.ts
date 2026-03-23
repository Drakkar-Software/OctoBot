import type { Execution } from "@/client"

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
        new Date(b.completed_at!).getTime() - new Date(a.completed_at!).getTime(),
    )
  return dated[0] ?? executions[executions.length - 1]
}
