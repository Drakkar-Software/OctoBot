import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/octochat", () => ({
  getSupportTicket: vi.fn(),
  sendAttachment: vi.fn(),
}))
vi.mock("@/lib/device-key", () => ({
  loadPassword: vi.fn(),
  loadClientKeys: vi.fn(),
}))

import { loadClientKeys, loadPassword } from "@/lib/device-key"
import { getSupportTicket, sendAttachment } from "@/lib/octochat"
import {
  buildLogsExportFilename,
  fetchWorkflowLogs,
  resolveDefaultHideLogTimings,
  shareWorkflowLogs,
} from "@/lib/support-share"

const mockedGetTicket = vi.mocked(getSupportTicket)
const mockedSendAttachment = vi.mocked(sendAttachment)
const mockedLoadPassword = vi.mocked(loadPassword)
const mockedLoadClientKeys = vi.mocked(loadClientKeys)
const fetchMock = vi.fn()

beforeEach(() => {
  mockedGetTicket.mockReset()
  mockedSendAttachment.mockReset().mockResolvedValue(undefined)
  mockedLoadPassword.mockReset().mockResolvedValue("pw")
  mockedLoadClientKeys.mockReset().mockResolvedValue(null)
  fetchMock.mockReset()
  vi.stubGlobal("localStorage", { getItem: vi.fn(() => "0xwallet") })
  vi.stubGlobal("fetch", fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function logsResponse(bytes: Uint8Array): Response {
  return {
    ok: true,
    status: 200,
    arrayBuffer: async () => bytes.buffer,
  } as unknown as Response
}

describe("buildLogsExportFilename", () => {
  it("produces a timestamped .zip name", () => {
    expect(buildLogsExportFilename()).toMatch(/^workflow-logs-.*\.zip$/)
  })
})

describe("fetchWorkflowLogs", () => {
  it("POSTs the task ids with an auth header and returns the zip file", async () => {
    fetchMock.mockResolvedValue(logsResponse(new Uint8Array([1, 2, 3])))

    const file = await fetchWorkflowLogs(["a", "b"])

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe("/api/v1/logs/export")
    expect(init.method).toBe("POST")
    expect(init.headers.Authorization).toMatch(/^Basic /)
    expect(JSON.parse(init.body)).toEqual({ task_ids: ["a", "b"] })
    expect(file.mime).toBe("application/zip")
    expect(file.name).toMatch(/^workflow-logs-.*\.zip$/)
    expect(Array.from(file.bytes)).toEqual([1, 2, 3])
  })

  it("throws a friendly error when the node has no logs (404)", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 404 } as Response)
    await expect(fetchWorkflowLogs(["a"])).rejects.toThrow(
      "No logs found for the selected OctoBots",
    )
  })

  it("throws on other non-ok responses", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500 } as Response)
    await expect(fetchWorkflowLogs(["a"])).rejects.toThrow(/500/)
  })

  it("POSTs remove_timing when requested", async () => {
    fetchMock.mockResolvedValue(logsResponse(new Uint8Array([1])))

    await fetchWorkflowLogs(["a"], { removeTiming: true })

    const [, init] = fetchMock.mock.calls[0]
    expect(JSON.parse(init.body)).toEqual({
      task_ids: ["a"],
      remove_timing: true,
    })
  })
})

describe("resolveDefaultHideLogTimings", () => {
  it("returns true when client keys are fully configured", async () => {
    mockedLoadClientKeys.mockResolvedValue({
      ecdsa_private: "ec",
      rsa_private: "rsa",
    })

    await expect(resolveDefaultHideLogTimings()).resolves.toBe(true)
  })

  it("returns false when keys are missing or incomplete", async () => {
    mockedLoadClientKeys.mockResolvedValue(null)
    await expect(resolveDefaultHideLogTimings()).resolves.toBe(false)

    mockedLoadClientKeys.mockResolvedValue({
      ecdsa_private: "ec",
      rsa_private: "",
    })
    await expect(resolveDefaultHideLogTimings()).resolves.toBe(false)
  })
})

describe("shareWorkflowLogs", () => {
  it("attaches the logs to an open ticket", async () => {
    mockedGetTicket.mockResolvedValue({
      status: "open",
      nodeId: "ticket-1",
      title: "Help",
      allTickets: [{ nodeId: "ticket-1", title: "Help" }],
    })
    fetchMock.mockResolvedValue(logsResponse(new Uint8Array([9])))

    const result = await shareWorkflowLogs(["task-a"])

    expect(result).toEqual({ status: "shared", nodeId: "ticket-1" })
    expect(mockedSendAttachment).toHaveBeenCalledTimes(1)
    const [nodeId, file, text] = mockedSendAttachment.mock.calls[0]
    expect(nodeId).toBe("ticket-1")
    expect(file.mime).toBe("application/zip")
    expect(file.name).toMatch(/^workflow-logs-.*\.zip$/)
    expect(text).toBe("Workflow logs")
  })

  it("passes remove_timing when sharing", async () => {
    mockedGetTicket.mockResolvedValue({
      status: "open",
      nodeId: "ticket-1",
      title: "Help",
      allTickets: [{ nodeId: "ticket-1", title: "Help" }],
    })
    fetchMock.mockResolvedValue(logsResponse(new Uint8Array([9])))

    await shareWorkflowLogs(["task-a"], { removeTiming: true })

    const [, init] = fetchMock.mock.calls[0]
    expect(JSON.parse(init.body)).toEqual({
      task_ids: ["task-a"],
      remove_timing: true,
    })
  })

  it.each([
    "none",
    "pending",
    "disabled",
  ] as const)("returns %s without fetching logs or attaching", async (status) => {
    mockedGetTicket.mockResolvedValue({ status } as Awaited<
      ReturnType<typeof getSupportTicket>
    >)

    const result = await shareWorkflowLogs(["task-a"])

    expect(result).toEqual({ status })
    expect(fetchMock).not.toHaveBeenCalled()
    expect(mockedSendAttachment).not.toHaveBeenCalled()
  })
})
