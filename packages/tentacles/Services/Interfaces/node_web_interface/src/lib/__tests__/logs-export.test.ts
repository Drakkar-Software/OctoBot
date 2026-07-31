import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/device-key", () => ({
  loadPassword: vi.fn(),
}))

import { loadPassword } from "@/lib/device-key"
import {
  buildAutomationLogsArchiveFilename,
  buildNodeLogsArchiveFilename,
  buildRunningAutomationsLatestLogsFilename,
  downloadAutomationLogsArchive,
  downloadBytesAsFile,
  downloadNodeLogsArchive,
  downloadRunningAutomationsLatestLogsArchive,
  fetchAutomationLogsArchive,
  fetchNodeLogsArchive,
} from "@/lib/logs-export"

const mockedLoadPassword = vi.mocked(loadPassword)
const fetchMock = vi.fn()

beforeEach(() => {
  mockedLoadPassword.mockReset().mockResolvedValue("pw")
  fetchMock.mockReset()
  vi.stubGlobal("localStorage", { getItem: vi.fn(() => "0xwallet") })
  vi.stubGlobal("fetch", fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function zipResponse(bytes: Uint8Array): Response {
  return {
    ok: true,
    status: 200,
    arrayBuffer: async () => bytes.buffer,
  } as unknown as Response
}

describe("buildNodeLogsArchiveFilename", () => {
  it("produces a timestamped .zip name", () => {
    expect(buildNodeLogsArchiveFilename()).toMatch(/^node-logs-.*\.zip$/)
  })
})

describe("buildAutomationLogsArchiveFilename", () => {
  it("produces a sanitized automation .zip name", () => {
    expect(
      buildAutomationLogsArchiveFilename("My Bot!", "task-123"),
    ).toMatch(/^automation-logs-My_Bot_-.*\.zip$/)
  })
})

describe("buildRunningAutomationsLatestLogsFilename", () => {
  it("produces a timestamped .zip name", () => {
    expect(buildRunningAutomationsLatestLogsFilename()).toMatch(
      /^running-automations-latest-logs-.*\.zip$/,
    )
  })
})

describe("fetchAutomationLogsArchive", () => {
  it("POSTs task_ids with auth and returns the zip file", async () => {
    fetchMock.mockResolvedValue(zipResponse(new Uint8Array([7, 8])))

    const file = await fetchAutomationLogsArchive(
      ["task-abc"],
      "automation-logs-test.zip",
    )

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe("/api/v1/logs/export")
    expect(init.method).toBe("POST")
    expect(init.headers.Authorization).toMatch(/^Basic /)
    expect(JSON.parse(init.body)).toEqual({ task_ids: ["task-abc"] })
    expect(file.mime).toBe("application/zip")
    expect(file.name).toBe("automation-logs-test.zip")
    expect(Array.from(file.bytes)).toEqual([7, 8])
  })

  it("throws a friendly error when no automation logs exist (404)", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 404 } as Response)
    await expect(
      fetchAutomationLogsArchive(["task-abc"], "automation-logs-test.zip"),
    ).rejects.toThrow("No logs found for the selected OctoBots")
  })

  it("POSTs latest_only when requested", async () => {
    fetchMock.mockResolvedValue(zipResponse(new Uint8Array([1])))

    await fetchAutomationLogsArchive(
      ["task-a", "task-b"],
      "running-automations-latest-logs-test.zip",
      { latestOnly: true },
    )

    const [, init] = fetchMock.mock.calls[0]
    expect(JSON.parse(init.body)).toEqual({
      task_ids: ["task-a", "task-b"],
      latest_only: true,
    })
  })
})

describe("fetchNodeLogsArchive", () => {
  it("POSTs an empty body with auth and returns the zip file", async () => {
    fetchMock.mockResolvedValue(zipResponse(new Uint8Array([1, 2, 3])))

    const file = await fetchNodeLogsArchive()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe("/api/v1/logs/export")
    expect(init.method).toBe("POST")
    expect(init.headers.Authorization).toMatch(/^Basic /)
    expect(JSON.parse(init.body)).toEqual({})
    expect(file.mime).toBe("application/zip")
    expect(file.name).toMatch(/^node-logs-.*\.zip$/)
    expect(Array.from(file.bytes)).toEqual([1, 2, 3])
  })

  it("throws a friendly error when the node has no logs (404)", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 404 } as Response)
    await expect(fetchNodeLogsArchive()).rejects.toThrow(
      "No logs found in the node logs folder",
    )
  })

  it("throws on other non-ok responses", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500 } as Response)
    await expect(fetchNodeLogsArchive()).rejects.toThrow(/500/)
  })

  it("throws instead of authenticating as a fabricated 'node' user when no session exists", async () => {
    // Regression test for https://github.com/Drakkar-Software/OctoBot/issues/3593
    vi.stubGlobal("localStorage", { getItem: vi.fn(() => null) })
    await expect(fetchNodeLogsArchive()).rejects.toThrow(
      "No active wallet session",
    )
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it("throws instead of sending an empty password when the device-stored password is missing", async () => {
    vi.stubGlobal("localStorage", { getItem: vi.fn(() => "0xwallet") })
    mockedLoadPassword.mockResolvedValue(null)
    await expect(fetchNodeLogsArchive()).rejects.toThrow(
      "No active wallet session",
    )
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

describe("downloadBytesAsFile", () => {
  it("creates a blob link and clicks it", () => {
    const createObjectURL = vi.fn(() => "blob:logs")
    const revokeObjectURL = vi.fn()
    const click = vi.fn()
    const appendChild = vi.fn()
    const removeChild = vi.fn()
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL })
    vi.stubGlobal("document", {
      createElement: () => ({ click, download: "" }),
      body: { appendChild, removeChild },
    })

    downloadBytesAsFile(new Uint8Array([9]), "node-logs.zip", "application/zip")

    expect(createObjectURL).toHaveBeenCalled()
    expect(click).toHaveBeenCalled()
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:logs")
  })
})

describe("downloadNodeLogsArchive", () => {
  it("fetches the archive and downloads it", async () => {
    fetchMock.mockResolvedValue(zipResponse(new Uint8Array([4, 5])))
    const createObjectURL = vi.fn(() => "blob:archive")
    const revokeObjectURL = vi.fn()
    const click = vi.fn()
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL })
    vi.stubGlobal("document", {
      createElement: () => ({ click, download: "" }),
      body: { appendChild: vi.fn(), removeChild: vi.fn() },
    })

    await downloadNodeLogsArchive()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(click).toHaveBeenCalled()
  })
})

describe("downloadAutomationLogsArchive", () => {
  it("fetches the automation archive and downloads it", async () => {
    fetchMock.mockResolvedValue(zipResponse(new Uint8Array([6, 7])))
    const createObjectURL = vi.fn(() => "blob:automation")
    const revokeObjectURL = vi.fn()
    const click = vi.fn()
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL })
    vi.stubGlobal("document", {
      createElement: () => ({ click, download: "" }),
      body: { appendChild: vi.fn(), removeChild: vi.fn() },
    })

    await downloadAutomationLogsArchive("task-abc", "My Bot")

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [, init] = fetchMock.mock.calls[0]
    expect(JSON.parse(init.body)).toEqual({ task_ids: ["task-abc"] })
    expect(click).toHaveBeenCalled()
  })
})

describe("downloadRunningAutomationsLatestLogsArchive", () => {
  it("fetches latest logs for running automations and downloads them", async () => {
    fetchMock.mockResolvedValue(zipResponse(new Uint8Array([8, 9])))
    const createObjectURL = vi.fn(() => "blob:running")
    const revokeObjectURL = vi.fn()
    const click = vi.fn()
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL })
    vi.stubGlobal("document", {
      createElement: () => ({ click, download: "" }),
      body: { appendChild: vi.fn(), removeChild: vi.fn() },
    })

    await downloadRunningAutomationsLatestLogsArchive(["task-a", "task-b"])

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [, init] = fetchMock.mock.calls[0]
    expect(JSON.parse(init.body)).toEqual({
      task_ids: ["task-a", "task-b"],
      latest_only: true,
    })
    expect(click).toHaveBeenCalled()
  })
})
