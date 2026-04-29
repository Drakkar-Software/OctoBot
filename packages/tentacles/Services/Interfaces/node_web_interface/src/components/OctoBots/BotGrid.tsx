import { Link } from "@tanstack/react-router"
import { Bot, Plus } from "lucide-react"

import type { Task_Output as Task } from "@/client"
import { Button } from "@/components/ui/button"
import { BotCard } from "./BotCard"

export function BotGrid({
  tasks,
  allTasksEmpty,
  selectedIds,
  onToggleSelect,
}: {
  tasks: Task[]
  allTasksEmpty: boolean
  selectedIds: Set<string>
  onToggleSelect: (id: string) => void
}) {
  if (allTasksEmpty) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
        <Bot className="size-10 text-muted-foreground/50" />
        <div>
          <p className="text-lg font-medium text-muted-foreground">No OctoBots yet</p>
          <p className="mt-1 text-sm text-muted-foreground/70">Start your first OctoBot or import a saved configuration.</p>
        </div>
        <Button asChild size="lg">
          <Link to="/octobots/new">
            <Plus className="size-4" />
            New OctoBot
          </Link>
        </Button>
      </div>
    )
  }

  if (tasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
        <Bot className="size-10 text-muted-foreground/50" />
        <div>
          <p className="text-lg font-medium text-muted-foreground">No OctoBots match this filter</p>
          <p className="mt-1 text-sm text-muted-foreground/70">Try another filter or search term.</p>
        </div>
        <Button asChild size="lg">
          <Link to="/octobots/new">
            <Plus className="size-4" />
            New OctoBot
          </Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {tasks.map((task) => (
        <BotCard
          key={task.id}
          task={task}
          selected={task.id ? selectedIds.has(task.id) : false}
          onToggleSelect={onToggleSelect}
        />
      ))}
    </div>
  )
}
