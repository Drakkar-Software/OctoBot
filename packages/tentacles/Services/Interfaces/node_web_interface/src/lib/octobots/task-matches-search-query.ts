import type { Task_Output as Task } from "@/client"
import { getActiveExecution } from "@/utils/executions"

export function taskMatchesSearchQuery(task: Task, query: string): boolean {
  const normalizedQuery = query.trim().toLowerCase()
  if (!normalizedQuery) return true
  const activeExec = getActiveExecution(task.executions)
  const haystack = [
    task.name ?? "",
    task.id ?? "",
    activeExec?.id ?? "",
    activeExec?.type ?? "",
  ]
    .join(" ")
    .toLowerCase()
  return haystack.includes(normalizedQuery)
}
