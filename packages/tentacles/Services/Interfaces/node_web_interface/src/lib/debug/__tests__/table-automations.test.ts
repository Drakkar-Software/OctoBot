import { describe, expect, it } from "vitest"

import type { AutomationState } from "@/client"
import {
  automationFilterHeadClass,
  automationFilterValues,
  filterAutomations,
  sortAutomations,
} from "@/lib/debug/table-automations"

function makeAutomation(
  overrides: Partial<AutomationState> = {},
): AutomationState {
  return {
    id: "auto-1",
    status: "running",
    metadata: { name: "Alpha", description: "" },
    ...overrides,
  }
}

describe("automationFilterHeadClass", () => {
  it("adds compact column class for compact columns", () => {
    expect(automationFilterHeadClass("orders")).toContain("w-0 px-2")
    expect(automationFilterHeadClass("name")).not.toContain("w-0 px-2")
  })
})

describe("automationFilterValues", () => {
  it("builds searchable values for each column", () => {
    const values = automationFilterValues(
      makeAutomation({ metadata: { name: "Alpha", description: "" } }),
    )
    expect(values.name).toBe("Alpha")
    expect(values.status).toBe("running")
  })
})

describe("filterAutomations", () => {
  it("filters rows by active column filters", () => {
    const rows = [
      makeAutomation({ id: "a1", metadata: { name: "Alpha", description: "" } }),
      makeAutomation({ id: "a2", metadata: { name: "Beta", description: "" } }),
    ]
    expect(filterAutomations(rows, { name: "beta" })).toHaveLength(1)
  })
})

describe("sortAutomations", () => {
  it("sorts by name ascending", () => {
    const rows = [
      makeAutomation({ id: "a2", metadata: { name: "Beta", description: "" } }),
      makeAutomation({ id: "a1", metadata: { name: "Alpha", description: "" } }),
    ]
    const sorted = sortAutomations(rows, { key: "name", dir: "asc" })
    expect(sorted.map((row) => row.id)).toEqual(["a1", "a2"])
  })
})
