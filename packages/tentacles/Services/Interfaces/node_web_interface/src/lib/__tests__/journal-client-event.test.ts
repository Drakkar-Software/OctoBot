import { beforeEach, describe, expect, it, vi } from "vitest"

import { OpenAPI } from "@/client"
import {
  buildJournalClientEventUrl,
  getOrCreateClientInstanceId,
  getUiBuild,
  reportUiJournalEvent,
} from "@/lib/journal-client-event"

const sessionStorageStore: Record<string, string> = {}
const sessionStorageMock = {
  getItem: (key: string) => sessionStorageStore[key] ?? null,
  setItem: (key: string, value: string) => {
    sessionStorageStore[key] = value
  },
  removeItem: (key: string) => {
    delete sessionStorageStore[key]
  },
  clear: () => {
    Object.keys(sessionStorageStore).forEach((key) => {
      delete sessionStorageStore[key]
    })
  },
  get length() {
    return Object.keys(sessionStorageStore).length
  },
}

vi.stubGlobal("sessionStorage", sessionStorageMock)

const fetchMock = vi.fn()

describe("getOrCreateClientInstanceId", () => {
  beforeEach(() => {
    sessionStorageMock.clear()
  })

  it("creates and reuses a session-scoped client instance id", () => {
    const firstId = getOrCreateClientInstanceId()
    const secondId = getOrCreateClientInstanceId()
    expect(firstId).toBeTruthy()
    expect(secondId).toBe(firstId)
  })
})

describe("getUiBuild", () => {
  it("returns the app version define", () => {
    expect(getUiBuild()).toBeTypeOf("string")
  })
})

describe("buildJournalClientEventUrl", () => {
  it("builds the journal client-event endpoint", () => {
    expect(buildJournalClientEventUrl("http://localhost:8000")).toBe(
      "http://localhost:8000/api/v1/journal/client-event",
    )
    expect(buildJournalClientEventUrl("http://localhost:8000/")).toBe(
      "http://localhost:8000/api/v1/journal/client-event",
    )
  })
})

describe("reportUiJournalEvent", () => {
  beforeEach(() => {
    sessionStorageMock.clear()
    OpenAPI.BASE = "http://localhost:8000"
    fetchMock.mockReset()
    fetchMock.mockResolvedValue({ ok: true })
    vi.stubGlobal("fetch", fetchMock)
  })

  it("posts ui events without throwing", async () => {
    await reportUiJournalEvent("ui_boot_failed", { error_name: "Error" })
    expect(fetchMock).toHaveBeenCalledOnce()
    const [requestUrl, requestInit] = fetchMock.mock.calls[0]
    expect(requestUrl).toBe(
      "http://localhost:8000/api/v1/journal/client-event",
    )
    expect(requestInit?.method).toBe("POST")
    const requestBody = JSON.parse(String(requestInit?.body))
    expect(requestBody.event).toBe("ui_boot_failed")
    expect(requestBody.client_instance_id).toBeTruthy()
    expect(requestBody.attributes.error_name).toBe("Error")
  })

  it("deduplicates events in the same session unless allowed", async () => {
    await reportUiJournalEvent("ui_auth_state_broken")
    await reportUiJournalEvent("ui_auth_state_broken")
    expect(fetchMock).toHaveBeenCalledOnce()

    await reportUiJournalEvent(
      "ui_client_storage_reset",
      { reset_tier: "full" },
      { allowDuplicate: true },
    )
    await reportUiJournalEvent(
      "ui_client_storage_reset",
      { reset_tier: "full" },
      { allowDuplicate: true },
    )
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it("swallows fetch failures", async () => {
    fetchMock.mockRejectedValue(new Error("network down"))
    await expect(
      reportUiJournalEvent("ui_fatal_render_error"),
    ).resolves.toBeUndefined()
  })
})
