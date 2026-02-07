import { useQuery } from "@tanstack/react-query"
import { Clock, CheckCircle2, ListTodo } from "lucide-react"

import type { TaskStatus } from "@/client"
import { TasksService } from "@/client"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

function getTaskMetricsQueryOptions() {
  return {
    queryFn: () => TasksService.getMetrics(),
    queryKey: ["task-metrics"],
    refetchInterval: 5000, // Refetch every 5 seconds
  }
}

interface TaskMetricsProps {
  selectedFilter?: TaskStatus | null
  onFilterChange?: (filter: TaskStatus | null) => void
}

export function TaskMetrics({ selectedFilter, onFilterChange }: TaskMetricsProps) {
  const { data: metrics, isLoading } = useQuery(getTaskMetricsQueryOptions())

  if (isLoading) {
    return (
      <div className="grid grid-cols-3 gap-2">
        {Array.from({ length: 3 }).map((_, index) => (
          <Card key={index} className="py-2">
            <CardHeader className="pb-2 px-4">
              <Skeleton className="h-3 w-16" />
            </CardHeader>
            <CardContent className="pt-0 px-4">
              <Skeleton className="h-5 w-8" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (!metrics || typeof metrics !== "object") {
    return null
  }

  const taskMetrics = metrics as { pending: number; scheduled: number; results: number }

  const handleCardClick = (filter: TaskStatus | null) => {
    if (onFilterChange) {
      // If clicking the same filter, reset to null (show all)
      if (selectedFilter === filter) {
        onFilterChange(null)
      } else {
        onFilterChange(filter)
      }
    }
  }

  return (
    <div className="grid grid-cols-3 gap-2">
      <Card 
        className={cn(
          "py-2",
          onFilterChange && "cursor-pointer hover:bg-muted/50 transition-colors",
          selectedFilter === "pending" && "ring-2 ring-primary"
        )}
        onClick={() => handleCardClick("pending")}
      >
        <CardHeader className="pb-0 px-4 space-y-0.5">
          <div className="flex items-center gap-1.5">
            <ListTodo className="h-3.5 w-3.5 text-muted-foreground" />
            <CardTitle className="text-sm font-medium">Pending</CardTitle>
          </div>
          <CardDescription className="text-xs">Tasks waiting to be executed</CardDescription>
        </CardHeader>
        <CardContent className="pt-0 px-4 -mt-1">
          <div className="text-xl font-bold">{taskMetrics.pending}</div>
        </CardContent>
      </Card>

      <Card 
        className={cn(
          "py-2",
          onFilterChange && "cursor-pointer hover:bg-muted/50 transition-colors",
          selectedFilter === "scheduled" && "ring-2 ring-primary"
        )}
        onClick={() => handleCardClick("scheduled")}
      >
        <CardHeader className="pb-0 px-4 space-y-0.5">
          <div className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-muted-foreground" />
            <CardTitle className="text-sm font-medium">Scheduled</CardTitle>
          </div>
          <CardDescription className="text-xs">Tasks scheduled for future execution</CardDescription>
        </CardHeader>
        <CardContent className="pt-0 px-4 -mt-1">
          <div className="text-xl font-bold">{taskMetrics.scheduled}</div>
        </CardContent>
      </Card>

      <Card 
        className={cn(
          "py-2",
          onFilterChange && "cursor-pointer hover:bg-muted/50 transition-colors",
          selectedFilter === "completed" && "ring-2 ring-primary"
        )}
        onClick={() => handleCardClick("completed")}
      >
        <CardHeader className="pb-0 px-4 space-y-0.5">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-muted-foreground" />
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
          </div>
          <CardDescription className="text-xs">Completed tasks with results available</CardDescription>
        </CardHeader>
        <CardContent className="pt-0 px-4 -mt-1">
          <div className="text-xl font-bold">{taskMetrics.results}</div>
        </CardContent>
      </Card>
    </div>
  )
}

