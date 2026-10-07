import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/journal-client-event", () => ({
  reportUiJournalEvent: vi.fn(),
}))

import { reportUiJournalEvent } from "@/lib/journal-client-event"
import {
  reportAuthStateBroken,
  reportInsecureContext,
} from "@/lib/shell-error-reporting"

const mockedReportUiJournalEvent = vi.mocked(reportUiJournalEvent)

const localStorageStore: Record<string, string> = {}
const localStorageMock = {
  getItem: (key: string) => localStorageStore[key] ?? null,
  setItem: (key: string, value: string) => {
    localStorageStore[key] = value
  },
  removeItem: (key: string) => {
    delete localStorageStore[key]
  },
  clear: () => {
    Object.keys(localStorageStore).forEach((key) => {
      delete localStorageStore[key]
    })
  },
}

describe("reportInsecureContext", () => {
  beforeEach(() => {
    mockedReportUiJournalEvent.mockReset()
  })

  it("posts ui_insecure_context with expected attributes", () => {
    reportInsecureContext({
      isSecureContext: false,
      hostname: "192.168.1.10",
    })

    expect(mockedReportUiJournalEvent).toHaveBeenCalledWith(
      "ui_insecure_context",
      {
        is_secure_context: false,
        hostname: "192.168.1.10",
      },
    )
  })
})

describe("reportAuthStateBroken", () => {
  beforeEach(() => {
    vi.stubGlobal("localStorage", localStorageMock)
    localStorageMock.clear()
    mockedReportUiJournalEvent.mockReset()
  })

  it("reports has_username when auth_username is stored", () => {
    localStorageMock.setItem("auth_username", "user@example.com")
    reportAuthStateBroken()

    expect(mockedReportUiJournalEvent).toHaveBeenCalledWith(
      "ui_auth_state_broken",
      {
        has_username: true,
        has_password_record: false,
      },
    )
  })

  it("reports has_username false when auth_username is absent", () => {
    reportAuthStateBroken()

    expect(mockedReportUiJournalEvent).toHaveBeenCalledWith(
      "ui_auth_state_broken",
      {
        has_username: false,
        has_password_record: false,
      },
    )
  })
})
