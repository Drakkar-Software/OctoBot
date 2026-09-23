import { describe, expect, it } from "vitest"

import type { TaskOutput as Task } from "@/client"
import {
  getStoppedTaskIdsForExport,
  shouldProcessExportEntry,
} from "@/lib/export-results-fetch"

function taskWithStatus(id: string, status: string): Task {
  return {
    id,
    executions: [{ status, completed_at: "2026-01-01T00:00:00Z" }],
  } as Task
}

describe("getStoppedTaskIdsForExport", () => {
  it("includes failed, completed, and cancelled tasks", () => {
    const tasks = [
      taskWithStatus("failed-1", "failed"),
      taskWithStatus("done-1", "completed"),
      taskWithStatus("cancel-1", "cancelled"),
    ]
    expect(getStoppedTaskIdsForExport(tasks).sort()).toEqual(
      ["cancel-1", "done-1", "failed-1"].sort(),
    )
  })

  it("excludes running and pending tasks", () => {
    const tasks = [
      taskWithStatus("run-1", "running"),
      taskWithStatus("pend-1", "pending"),
      taskWithStatus("done-1", "completed"),
    ]
    expect(getStoppedTaskIdsForExport(tasks)).toEqual(["done-1"])
  })

  it("omits tasks without id", () => {
    const tasks = [taskWithStatus("", "completed")]
    expect(getStoppedTaskIdsForExport(tasks)).toEqual([])
  })
})

describe("shouldProcessExportEntry", () => {
  it("returns true when result has plaintext payload", () => {
    expect(
      shouldProcessExportEntry({ result: JSON.stringify({ ok: true }) }),
    ).toBe(true)
  })

  it("returns false for empty result with error", () => {
    expect(
      shouldProcessExportEntry({ result: "", error: "max_attempts_exceeded" }),
    ).toBe(false)
  })

  it("returns true when both result and error are present", () => {
    expect(
      shouldProcessExportEntry({
        result: '{"state":{}}',
        error: "partial",
      }),
    ).toBe(true)
  })
})
