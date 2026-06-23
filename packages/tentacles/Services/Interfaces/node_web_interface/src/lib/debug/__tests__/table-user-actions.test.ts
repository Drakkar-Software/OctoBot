import { describe, expect, it } from "vitest"

import type { UserAction } from "@/client"
import {
  filterUserActions,
  sortUserActions,
  userActionFilterValues,
} from "@/lib/debug/table-user-actions"

describe("userActionFilterValues", () => {
  it("builds searchable values for user actions", () => {
    const values = userActionFilterValues({
      id: "ua-1",
      status: "failed",
      configuration: { action_type: "automation_stop", id: "auto-1" },
    } as UserAction)
    expect(values.actionType).toBe("automation_stop")
    expect(values.status).toBe("failed")
  })
})

describe("filterUserActions", () => {
  it("filters by action type", () => {
    const rows = [
      {
        id: "ua-1",
        configuration: { action_type: "automation_stop", id: "a1" },
      },
      {
        id: "ua-2",
        configuration: {
          action_type: "account_edit",
          id: "acc",
          configuration: {},
        },
      },
    ] as unknown as UserAction[]
    expect(filterUserActions(rows, { actionType: "account" })).toHaveLength(1)
  })
})

describe("sortUserActions", () => {
  it("sorts by id ascending", () => {
    const rows: UserAction[] = [{ id: "b" }, { id: "a" }]
    const sorted = sortUserActions(rows, { key: "id", dir: "asc" })
    expect(sorted.map((row) => row.id)).toEqual(["a", "b"])
  })
})
