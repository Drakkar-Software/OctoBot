import { describe, expect, it } from "vitest"

import type { Strategy } from "@/client"
import {
  compareStrategiesByIdThenUpdated,
  filterStrategies,
  sortStrategies,
  strategyFilterValues,
} from "@/lib/debug/table-strategies"

function makeStrategy(overrides: Partial<Strategy> = {}): Strategy {
  return {
    id: "strat-1",
    version: "1.0.0",
    name: "Alpha",
    reference_market: "USDT",
    configuration: { configuration_type: "generic_process", profile_data: {} },
    updated_at: "2024-01-01T00:00:00.000Z",
    ...overrides,
  } as Strategy
}

describe("strategyFilterValues", () => {
  it("builds searchable strategy values", () => {
    const values = strategyFilterValues(makeStrategy())
    expect(values.name).toBe("Alpha")
    expect(values.configType).toBe("generic_process")
  })
})

describe("filterStrategies", () => {
  it("filters by strategy name", () => {
    const rows = [
      makeStrategy({ id: "s1", name: "Alpha" }),
      makeStrategy({ id: "s2", name: "Beta" }),
    ]
    expect(filterStrategies(rows, { name: "beta" })).toHaveLength(1)
  })
})

describe("compareStrategiesByIdThenUpdated", () => {
  it("breaks ties by updated_at descending", () => {
    const left = makeStrategy({
      id: "same",
      updated_at: "2024-01-01T00:00:00.000Z",
    })
    const right = makeStrategy({
      id: "same",
      updated_at: "2024-06-01T00:00:00.000Z",
    })
    expect(compareStrategiesByIdThenUpdated(left, right)).toBeGreaterThan(0)
  })
})

describe("sortStrategies", () => {
  it("sorts by name and uses tie-breaker", () => {
    const rows = [
      makeStrategy({ id: "s2", name: "Beta" }),
      makeStrategy({ id: "s1", name: "Alpha" }),
    ]
    const sorted = sortStrategies(rows, { key: "name", dir: "asc" })
    expect(sorted.map((row) => row.id)).toEqual(["s1", "s2"])
  })
})
