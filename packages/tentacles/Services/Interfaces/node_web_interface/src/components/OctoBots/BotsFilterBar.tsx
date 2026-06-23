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
    <div className="inline-flex items-center gap-1 rounded-pill border border-rule-soft bg-surface-soft p-1 self-start">
      {filters.map((f) => {
        const active = filterValue === f.value
        return (
          <button
            type="button"
            key={f.value}
            onClick={() => onFilterChange(f.value)}
            className={cn(
              "rounded-pill px-3.5 py-1.5 text-sm font-medium transition-all",
              active
                ? "bg-primary text-primary-foreground shadow-glow"
                : "text-muted-foreground hover:text-foreground hover:bg-surface-mid",
            )}
          >
            {f.label}
            <span
              className={cn(
                "ml-1.5 tabular-nums text-xs",
                active ? "opacity-70" : "opacity-50",
              )}
            >
              {counts[f.value]}
            </span>
          </button>
        )
      })}
      <div className="mx-1 h-4 w-px bg-rule-soft" />
      <div className="relative flex items-center">
        <Search className="pointer-events-none absolute left-2.5 size-3.5 text-muted-foreground" />
        <input
          value={searchValue}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search..."
          className="h-7 w-32 rounded-pill bg-transparent pl-8 pr-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none"
        />
        {searchValue && (
          <button
            type="button"
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
