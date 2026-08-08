import { afterEach, describe, expect, it, vi } from "vitest"

import type { ChildOctoBotProcessState } from "@/client"
import {
  buildProcessBotUrl,
  formatProcessAddress,
} from "@/utils/process-address"

describe("buildProcessBotUrl", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("uses the browser hostname and child web port over http", () => {
    vi.stubGlobal("window", {
      location: { hostname: "192.168.1.10" },
    })

    expect(buildProcessBotUrl(5001)).toBe("http://192.168.1.10:5001")
  })
})

describe("formatProcessAddress", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("returns hostname:port from the browser-origin child url", () => {
    vi.stubGlobal("window", {
      location: { hostname: "100.64.0.1" },
    })

    const childProcess = {
      http_base_url: "http://127.0.0.1:5001",
      web_port: 5001,
      init_state_ok: true,
    } satisfies ChildOctoBotProcessState

    expect(formatProcessAddress(childProcess)).toBe("100.64.0.1:5001")
  })
})
