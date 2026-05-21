import type { Task_Output as Task } from "@/client"
import { getActiveExecution } from "@/utils/executions"

export interface TaskErrorInfo {
  status: string | null
  message: string | null
}

export function resolveTaskError(task: Task): TaskErrorInfo {
  const exec = getActiveExecution(task.executions)
  return {
    status: task.error ?? exec?.error ?? null,
    message: task.error_message ?? exec?.error_message ?? null,
  }
}

export function formatTaskErrorDisplay(task: Task): string | null {
  const { status, message } = resolveTaskError(task)
  if (status && message) return `${status}: ${message}`
  return status ?? message ?? null
}
