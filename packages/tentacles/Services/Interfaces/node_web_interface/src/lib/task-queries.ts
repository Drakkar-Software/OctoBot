import { TasksService } from "@/client"

export function getTasksQueryOptions() {
  return {
    queryFn: () => TasksService.getTasks({ page: 1, limit: 100 }),
    queryKey: ["tasks"],
    refetchInterval: 5_000,
    // A hidden tab has nothing to show: stop polling until it is visible again.
    refetchIntervalInBackground: false,
  }
}
