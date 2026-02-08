import { ReactNode } from "react"

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { SearchInput } from "@/components/Common/SearchInput"

export type FilterOption = {
  value: string
  label: string
}

interface CollectionHeaderProps {
  title: string
  description?: string
  action?: ReactNode
  searchValue: string
  onSearchChange: (value: string) => void
  searchPlaceholder?: string
  filters: FilterOption[]
  filterValue: string
  onFilterChange: (value: string) => void
}

export function CollectionHeader({
  title,
  description,
  action,
  searchValue,
  onSearchChange,
  searchPlaceholder,
  filters,
  filterValue,
  onFilterChange,
}: CollectionHeaderProps) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          {description && (
            <p className="text-muted-foreground">{description}</p>
          )}
        </div>
        {action}
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <SearchInput
          value={searchValue}
          onChange={onSearchChange}
          placeholder={searchPlaceholder}
          className="min-w-[240px] flex-1"
        />
        <Tabs
          value={filterValue}
          onValueChange={onFilterChange}
          className="w-full sm:w-auto"
        >
          <TabsList>
            {filters.map((filter) => (
              <TabsTrigger key={filter.value} value={filter.value}>
                {filter.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>
    </div>
  )
}
