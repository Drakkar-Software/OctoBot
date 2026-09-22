import type { TaskOutput as Task } from "@/client"
import { getActiveExecution, getStatusGroup } from "@/utils/executions"

export function getStoppedTaskIdsForExport(tasks: Task[]): string[] {
  return tasks
    .filter((task) => {
      const status = getActiveExecution(task.executions)?.status
      return getStatusGroup(status) === "stopped"
    })
    .map((task) => task.id ?? "")
    .filter(Boolean)
}

export function shouldProcessExportEntry(entry: {
  result?: string
  error?: string
}): boolean {
  return Boolean(entry.result)
}
