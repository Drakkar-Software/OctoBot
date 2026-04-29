import { Search, X } from "lucide-react"

import { cn } from "@/lib/utils"
import { filters, type TaskFilterGroup } from "@/utils/task-status"

export function BotsFilterBar({
  filterValue,
  searchValue,
  counts,
  onFilterChange,
  onSearchChange,
}: {
  filterValue: TaskFilterGroup
  searchValue: string
  counts: Record<TaskFilterGroup, number>
  onFilterChange: (value: TaskFilterGroup) => void
  onSearchChange: (value: string) => void
}) {
  return (
    <div className="inline-flex items-center rounded-lg border p-0.5 self-start">
      {filters.map((f) => {
        const active = filterValue === f.value
        return (
          <button
            key={f.value}
            onClick={() => onFilterChange(f.value)}
            className={cn(
              "rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors",
              active
                ? "bg-foreground text-background shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {f.label}
            <span className={cn("ml-1.5 tabular-nums", active ? "text-background/70" : "text-muted-foreground/60")}>
              {counts[f.value]}
            </span>
          </button>
        )
      })}
      <div className="mx-1 h-5 w-px bg-border" />
      <div className="relative flex items-center">
        <Search className="pointer-events-none absolute left-2.5 size-3.5 text-muted-foreground" />
        <input
          value={searchValue}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search..."
          className="h-7 w-32 rounded-md bg-transparent pl-8 pr-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none"
        />
        {searchValue && (
          <button
            onClick={() => onSearchChange("")}
            className="absolute right-1.5 text-muted-foreground hover:text-foreground"
          >
            <X className="size-3" />
          </button>
        )}
      </div>
    </div>
  )
}
