import { describe, expect, it } from "vitest"

import { matchesDebugStatusColumnFilter } from "@/lib/debug/display-utils"
import {
  compareNumbers,
  compareStrings,
  getActiveFilterKeys,
  hasActiveFilters,
  matchesColumnFilter,
  matchesTableColumnFilter,
  parseSortTime,
  setColumnFilter,
  toggleSort,
} from "@/lib/table"

describe("parseSortTime", () => {
  it("returns negative infinity for missing or invalid values", () => {
    expect(parseSortTime(null)).toBe(Number.NEGATIVE_INFINITY)
    expect(parseSortTime("not-a-date")).toBe(Number.NEGATIVE_INFINITY)
  })

  it("returns milliseconds for valid ISO timestamps", () => {
    expect(parseSortTime("2024-01-01T00:00:00.000Z")).toBe(
      new Date("2024-01-01T00:00:00.000Z").getTime(),
    )
  })
})

describe("compareStrings", () => {
  it("sorts ascending and descending", () => {
    expect(compareStrings("a", "b", "asc")).toBeLessThan(0)
    expect(compareStrings("a", "b", "desc")).toBeGreaterThan(0)
  })
})

describe("compareNumbers", () => {
  it("sorts ascending and descending", () => {
    expect(compareNumbers(1, 2, "asc")).toBe(-1)
    expect(compareNumbers(1, 2, "desc")).toBe(1)
  })
})

describe("toggleSort", () => {
  it("flips direction on the same key", () => {
    expect(toggleSort({ key: "id", dir: "asc" }, "id")).toEqual({
      key: "id",
      dir: "desc",
    })
  })

  it("resets to ascending on a new key", () => {
    expect(toggleSort({ key: "id", dir: "desc" }, "name")).toEqual({
      key: "name",
      dir: "asc",
    })
  })
})

describe("hasActiveFilters", () => {
  it("returns false when all filters are empty", () => {
    expect(hasActiveFilters({ id: "", status: "  " })).toBe(false)
  })

  it("returns true when any filter has text", () => {
    expect(hasActiveFilters({ id: "abc" })).toBe(true)
  })
})

describe("getActiveFilterKeys", () => {
  it("returns only keys with non-empty trimmed values", () => {
    expect(getActiveFilterKeys({ id: "x", status: " ", name: "bot" })).toEqual([
      "id",
      "name",
    ])
  })
})

describe("setColumnFilter", () => {
  it("removes the key when value is blank", () => {
    expect(setColumnFilter({ id: "old" }, "id", "   ")).toEqual({})
  })

  it("sets the filter value when non-empty", () => {
    expect(setColumnFilter({}, "id", "abc")).toEqual({ id: "abc" })
  })
})

describe("matchesColumnFilter", () => {
  it("matches case-insensitive substrings", () => {
    expect(matchesColumnFilter("Running Bot", "run")).toBe(true)
  })

  it("does not match completed when filtering failed substring", () => {
    expect(matchesColumnFilter("completed", "failed")).toBe(false)
  })
})

describe("matchesTableColumnFilter", () => {
  it("delegates status columns to the status matcher", () => {
    expect(
      matchesTableColumnFilter(
        "status",
        { status: "running" },
        "failed",
        "failed",
        matchesDebugStatusColumnFilter,
      ),
    ).toBe(true)
    expect(
      matchesTableColumnFilter(
        "status",
        { status: "completed" },
        "failed",
        "completed",
        matchesDebugStatusColumnFilter,
      ),
    ).toBe(false)
  })

  it("uses text matching for non-status columns", () => {
    expect(
      matchesTableColumnFilter("name", { name: "Alpha bot" }, "alpha"),
    ).toBe(true)
  })
})
