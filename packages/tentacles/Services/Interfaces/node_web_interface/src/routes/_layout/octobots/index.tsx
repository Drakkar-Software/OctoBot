import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Loader2 } from "lucide-react"
import { Suspense, useCallback, useMemo, useState } from "react"

import type { Task_Output as Task } from "@/client"
import { BotGrid } from "@/components/OctoBots/BotGrid"
import { BotsFilterBar } from "@/components/OctoBots/BotsFilterBar"
import { SelectionToolbar } from "@/components/OctoBots/SelectionToolbar"
import { getTasksQueryOptions } from "@/lib/task-queries"
import { getActiveExecution } from "@/utils/executions"
import {
  getTaskFilterGroup,
  getTaskSortDate,
  type TaskFilterGroup,
} from "@/utils/task-status"

function BotsContent() {
  const { data: tasks } = useSuspenseQuery(getTasksQueryOptions())
  const [filterValue, setFilterValue] = useState<TaskFilterGroup>("active")
  const [searchValue, setSearchValue] = useState("")
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  const filteredTasks = useMemo(() => {
    const query = searchValue.trim().toLowerCase()
    const matched = tasks.filter((task: Task) => {
      const activeExec = getActiveExecution(task.executions)
      const inFilter = getTaskFilterGroup(task) === filterValue
      const inSearch = query
        ? `${task.name ?? ""} ${activeExec?.type ?? ""}`
            .toLowerCase()
            .includes(query)
        : true
      return inFilter && inSearch
    })
    const tagged = matched.map((task: Task) => {
      const d = getTaskSortDate(task)
      return { task, ts: d ? new Date(d).getTime() : -Infinity }
    })
    tagged.sort((a, b) => b.ts - a.ts)
    return tagged.map(({ task }) => task)
  }, [tasks, filterValue, searchValue])

  const counts = useMemo(() => {
    const c = { active: 0, completed: 0, errored: 0 }
    for (const task of tasks) {
      c[getTaskFilterGroup(task)]++
    }
    return c
  }, [tasks])

  const handleToggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const handleSelectAll = () => {
    setSelectedIds(new Set(filteredTasks.map((t) => t.id!).filter(Boolean)))
  }

  const handleDeselectAll = () => {
    setSelectedIds(new Set())
  }

  return (
    <div className="flex flex-col gap-6">
      <BotsFilterBar
        filterValue={filterValue}
        searchValue={searchValue}
        counts={counts}
        onFilterChange={setFilterValue}
        onSearchChange={setSearchValue}
      />
      {selectedIds.size > 0 && (
        <SelectionToolbar
          selectedIds={selectedIds}
          filteredTasks={filteredTasks}
          allTasks={tasks}
          onSelectAll={handleSelectAll}
          onDeselectAll={handleDeselectAll}
          onDeleted={handleDeselectAll}
        />
      )}
      <BotGrid
        tasks={filteredTasks}
        allTasksEmpty={tasks.length === 0}
        selectedIds={selectedIds}
        onToggleSelect={handleToggleSelect}
      />
    </div>
  )
}

export const Route = createFileRoute("/_layout/octobots/")({
  component: BotsIndex,
  head: () => ({
    meta: [{ title: "OctoBots" }],
  }),
})

function BotsIndex() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col items-center justify-center gap-3 py-40 text-muted-foreground">
          <Loader2 className="size-8 animate-spin" />
          <span className="text-sm">Loading OctoBots...</span>
        </div>
      }
    >
      <BotsContent />
    </Suspense>
  )
}
