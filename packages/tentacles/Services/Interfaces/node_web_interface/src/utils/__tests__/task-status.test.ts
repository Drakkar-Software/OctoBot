import { describe, expect, it } from "vitest"

import type { TaskOutput as Task } from "@/client"
import { getTaskFilterGroup, getTaskMetaStatus } from "@/utils/task-status"

function taskWithExecStatus(
  status: string,
  executionError?: string,
): Task {
  return {
    id: "task-1",
    executions: [
      {
        status,
        error: executionError,
        completed_at: "2026-01-01T00:00:00Z",
      },
    ],
  } as Task
}

describe("getTaskMetaStatus", () => {
  it("returns cancelled when execution was cancelled even with exec error", () => {
    const task = taskWithExecStatus("cancelled", "user_stopped")
    expect(getTaskMetaStatus(task)).toBe("cancelled")
  })

  it("returns errored for failed or exec error", () => {
    expect(getTaskMetaStatus(taskWithExecStatus("failed"))).toBe("errored")
    expect(getTaskMetaStatus(taskWithExecStatus("completed", "boom"))).toBe(
      "errored",
    )
  })

  it("returns raw status for completed success", () => {
    expect(getTaskMetaStatus(taskWithExecStatus("completed"))).toBe("completed")
  })
})

describe("getTaskFilterGroup", () => {
  it("maps cancelled executions to errored", () => {
    const task = taskWithExecStatus("cancelled")
    expect(getTaskFilterGroup(task)).toBe("errored")
    expect(getTaskFilterGroup(task)).not.toBe("completed")
  })

  it("maps failed and completed unchanged", () => {
    expect(getTaskFilterGroup(taskWithExecStatus("failed"))).toBe("errored")
    expect(getTaskFilterGroup(taskWithExecStatus("completed"))).toBe(
      "completed",
    )
  })

  it("maps running to active", () => {
    expect(getTaskFilterGroup(taskWithExecStatus("running"))).toBe("active")
  })

  it("maps execution error to errored even when status is completed", () => {
    expect(getTaskFilterGroup(taskWithExecStatus("completed", "boom"))).toBe(
      "errored",
    )
  })
})
