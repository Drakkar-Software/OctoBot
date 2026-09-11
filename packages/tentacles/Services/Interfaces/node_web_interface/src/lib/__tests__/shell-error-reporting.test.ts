import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/journal-client-event", () => ({
  getUiBuild: vi.fn(() => "test-build"),
  reportUiJournalEvent: vi.fn(),
}))

import {
  getUiBuild,
  reportUiJournalEvent,
} from "@/lib/journal-client-event"
import { reportInsecureContext } from "@/lib/shell-error-reporting"

const mockedReportUiJournalEvent = vi.mocked(reportUiJournalEvent)
const mockedGetUiBuild = vi.mocked(getUiBuild)

describe("reportInsecureContext", () => {
  beforeEach(() => {
    mockedReportUiJournalEvent.mockReset()
    mockedGetUiBuild.mockReturnValue("test-build")
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
        ui_build: "test-build",
      },
    )
  })
})
