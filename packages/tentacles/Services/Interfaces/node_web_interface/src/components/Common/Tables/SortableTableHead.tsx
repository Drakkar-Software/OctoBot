import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react"

import { TableHead } from "@/components/ui/table"
import type { SortState } from "@/lib/table-types"

type SortableTableHeadProps<K extends string> = {
  label: string
  sortKey: K
  sort: SortState<K>
  onSort: (key: K) => void
  className?: string
}

export function SortableTableHead<K extends string>({
  label,
  sortKey,
  sort,
  onSort,
  className,
}: SortableTableHeadProps<K>) {
  const active = sort.key === sortKey
  const Icon = active
    ? sort.dir === "asc"
      ? ArrowUp
      : ArrowDown
    : ArrowUpDown
  return (
    <TableHead className={className}>
      <button
        type="button"
        className="inline-flex items-center gap-1 hover:text-foreground text-inherit -ml-1 px-1 rounded-sm"
        onClick={() => onSort(sortKey)}
      >
        {label}
        <Icon
          className={`size-3.5 shrink-0 ${active ? "text-foreground" : "text-muted-foreground/60"}`}
        />
      </button>
    </TableHead>
  )
}
