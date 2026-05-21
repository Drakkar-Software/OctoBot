import { describe, expect, it } from "vitest"

import type { Task_Output as Task } from "@/client"
import { formatTaskErrorDisplay, resolveTaskError } from "@/utils/task-errors"

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: "task-1",
    executions: [],
    ...overrides,
  }
}

describe("resolveTaskError", () => {
  it("prefers task-level fields over execution fields", () => {
    const task = makeTask({
      error: "TASK_ERROR",
      error_message: "Task message",
      executions: [
        {
          id: "exec-1",
          error: "EXEC_ERROR",
          error_message: "Exec message",
        },
      ],
    })
    expect(resolveTaskError(task)).toEqual({
      status: "TASK_ERROR",
      message: "Task message",
    })
  })

  it("falls back to active execution fields", () => {
    const task = makeTask({
      executions: [
        {
          id: "exec-1",
          error: "EXEC_ERROR",
          error_message: "Exec message",
        },
      ],
    })
    expect(resolveTaskError(task)).toEqual({
      status: "EXEC_ERROR",
      message: "Exec message",
    })
  })

  it("returns nulls when no error fields exist", () => {
    expect(resolveTaskError(makeTask())).toEqual({
      status: null,
      message: null,
    })
  })
})

describe("formatTaskErrorDisplay", () => {
  it("combines status and message with a colon", () => {
    expect(
      formatTaskErrorDisplay(
        makeTask({
          error: "INTERNAL_ERROR",
          error_message: "Balance below threshold",
        }),
      ),
    ).toBe("INTERNAL_ERROR: Balance below threshold")
  })

  it("returns status alone when message is missing", () => {
    expect(formatTaskErrorDisplay(makeTask({ error: "INTERNAL_ERROR" }))).toBe(
      "INTERNAL_ERROR",
    )
  })

  it("returns message alone when status is missing", () => {
    expect(
      formatTaskErrorDisplay(
        makeTask({ error_message: "Something went wrong" }),
      ),
    ).toBe("Something went wrong")
  })

  it("returns null when neither field is present", () => {
    expect(formatTaskErrorDisplay(makeTask())).toBeNull()
  })
})
