import { TasksService } from "@/client"

export function getTasksQueryOptions() {
  return {
    queryFn: () => TasksService.getTasks({ page: 1, limit: 100 }),
    queryKey: ["tasks"],
    refetchInterval: 2_000,
  }
}
