import { describe, expect, it } from "vitest"

import type { TaskOutput as Task } from "@/client"
import { taskMatchesSearchQuery } from "@/lib/octobots/task-matches-search-query"

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: "90f49c03-3d0c-4727-9ca9-51fbe4e5dacb",
    name: "Simu trade 1",
    content: null,
    is_encrypted: false,
    executions: [
      {
        id: "90f49c03-3d0c-4727-9ca9-51fbe4e5dacb_7",
        name: null,
        status: "completed",
        type: "execute_actions",
        completed_at: "2026-01-01T00:00:00Z",
      },
    ],
    ...overrides,
  }
}

describe("taskMatchesSearchQuery", () => {
  it("matches empty query", () => {
    expect(taskMatchesSearchQuery(makeTask(), "")).toBe(true)
    expect(taskMatchesSearchQuery(makeTask(), "   ")).toBe(true)
  })

  it("matches task name", () => {
    expect(taskMatchesSearchQuery(makeTask(), "simu")).toBe(true)
  })

  it("matches partial parent task id", () => {
    expect(taskMatchesSearchQuery(makeTask(), "90f49c03")).toBe(true)
  })

  it("matches active execution id", () => {
    expect(taskMatchesSearchQuery(makeTask(), "_7")).toBe(true)
  })

  it("returns false when haystack does not contain query", () => {
    expect(taskMatchesSearchQuery(makeTask(), "not-in-haystack")).toBe(false)
  })
})
