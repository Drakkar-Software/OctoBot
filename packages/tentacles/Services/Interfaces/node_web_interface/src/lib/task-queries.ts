import { type TaskOutput, TasksService } from "@/client"

// Must match octobot_node.constants.TASKS_LIST_MAX_PAGE_LIMIT (tasks beyond cap are not shown).
const TASK_LIST_FETCH_LIMIT = 500
const TASKS_LIST_REFETCH_INTERVAL_MS = 5_000

export function getTasksQueryOptions() {
  return {
    queryFn: async (): Promise<TaskOutput[]> => {
      const response = await TasksService.tasksGetTasks({
        query: { page: 1, limit: TASK_LIST_FETCH_LIMIT },
        throwOnError: true,
      })
      return response.data
    },
    queryKey: ["tasks"],
    refetchInterval: TASKS_LIST_REFETCH_INTERVAL_MS,
  }
}
