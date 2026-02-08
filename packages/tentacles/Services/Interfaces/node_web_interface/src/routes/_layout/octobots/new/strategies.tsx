import { createFileRoute } from "@tanstack/react-router"
import { Plus } from "lucide-react"
import { useMemo, useState } from "react"

import { CollectionHeader } from "@/components/Common/CollectionHeader"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

type Strategy = {
  id: string
  name: string
  description: string
  difficulty: "easy" | "medium" | "hard"
  origin: "official" | "community"
}

const strategies: Strategy[] = [
  {
    id: "grid",
    name: "Grid Starter",
    description: "Simple grid strategy for range markets.",
    difficulty: "easy",
    origin: "official",
  },
  {
    id: "trend",
    name: "Trend Pulse",
    description: "Trend-following strategy with momentum checks.",
    difficulty: "medium",
    origin: "community",
  },
  {
    id: "market-making",
    name: "Market Making",
    description: "Liquidity providing with spread management.",
    difficulty: "hard",
    origin: "official",
  },
]

const filters = [
  { value: "all", label: "All" },
  { value: "official", label: "Official" },
  { value: "community", label: "Community" },
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
]

export const Route = createFileRoute("/_layout/octobots/new/strategies")({
  component: StrategyChooser,
  head: () => ({
    meta: [{ title: "Pre-configured strategies" }],
  }),
})

function StrategyChooser() {
  const [searchValue, setSearchValue] = useState("")
  const [filterValue, setFilterValue] = useState("all")

  const filtered = useMemo(() => {
    const query = searchValue.trim().toLowerCase()
    return strategies.filter((strategy) => {
      const matchesFilter =
        filterValue === "all"
          ? true
          : strategy.origin === filterValue || strategy.difficulty === filterValue
      const matchesQuery = query
        ? `${strategy.name} ${strategy.description}`.toLowerCase().includes(query)
        : true
      return matchesFilter && matchesQuery
    })
  }, [filterValue, searchValue])

  return (
    <div className="flex flex-col gap-8">
      <CollectionHeader
        title="Pre-configured strategies"
        description="Pick a strategy and launch your OctoBot quickly."
        action={
          <Button disabled size="lg">
            <Plus className="size-4" />
            Create my own strategy
          </Button>
        }
        searchValue={searchValue}
        onSearchChange={setSearchValue}
        searchPlaceholder="Search strategies..."
        filters={filters}
        filterValue={filterValue}
        onFilterChange={setFilterValue}
      />
      {filtered.length === 0 ? (
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle>No strategies found</CardTitle>
            <CardDescription>Try another filter or search.</CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {filtered.map((strategy) => (
            <Card key={strategy.id} className="transition-shadow hover:shadow-md">
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle>{strategy.name}</CardTitle>
                    <CardDescription>{strategy.description}</CardDescription>
                  </div>
                  <Badge variant="secondary">{strategy.origin}</Badge>
                </div>
              </CardHeader>
              <CardContent className="flex items-center justify-between text-sm text-muted-foreground">
                <span>Difficulty: {strategy.difficulty}</span>
                <Button variant="outline" size="sm">
                  Use strategy
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
