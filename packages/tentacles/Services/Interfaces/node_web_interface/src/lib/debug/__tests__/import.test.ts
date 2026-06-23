import { describe, expect, it, vi } from "vitest"

import type { DebugState, Strategy } from "@/client"
import {
  buildDebugExportFilename,
  debugStateToFile,
  downloadDebugStateJson,
  formatImportedSnapshotContents,
  getDebugStateLatestUpdatedAt,
  parseDebugStateJson,
  sanitizeDebugExportFilename,
  serializeDebugStateJson,
  summarizeImportedDebugState,
} from "@/lib/debug/import"

const minimalDebugStateJson = JSON.stringify({
  version: "1.0.0",
  debug: {
    automations: [],
    user_actions: [],
  },
})

describe("parseDebugStateJson", () => {
  it("accepts a valid minimal DebugState", () => {
    const result = parseDebugStateJson(minimalDebugStateJson)
    expect("state" in result).toBe(true)
    if ("state" in result) {
      expect(result.state.version).toBe("1.0.0")
      expect(result.state.debug?.automations).toEqual([])
      expect(result.state.debug?.user_actions).toEqual([])
      expect(result.state.debug?.accounts).toEqual([])
    }
  })

  it("rejects empty input", () => {
    expect(parseDebugStateJson("   ")).toEqual({
      error: "JSON cannot be empty",
    })
  })

  it("rejects invalid JSON", () => {
    const result = parseDebugStateJson("{")
    expect("error" in result).toBe(true)
  })

  it("rejects missing version", () => {
    const result = parseDebugStateJson(
      JSON.stringify({ debug: { automations: [], user_actions: [] } }),
    )
    expect(result).toEqual({
      error: 'Payload must include a string "version" field',
    })
  })

  it("rejects missing debug.automations array", () => {
    const result = parseDebugStateJson(
      JSON.stringify({
        version: "1.0.0",
        debug: { user_actions: [] },
      }),
    )
    expect(result).toEqual({ error: "debug.automations must be an array" })
  })
})

describe("getDebugStateLatestUpdatedAt", () => {
  it("returns null when debug is empty", () => {
    const state: DebugState = {
      version: "1.0.0",
      debug: {
        automations: [],
        user_actions: [],
      },
    }
    expect(getDebugStateLatestUpdatedAt(state)).toBeNull()
  })

  it("returns the latest timestamp across entities", () => {
    const state: DebugState = {
      version: "1.0.0",
      debug: {
        automations: [
          {
            id: "auto-1",
            status: "running",
            metadata: {
              name: "A",
              description: "",
              updated_at: "2024-01-01T10:00:00.000Z",
            },
            actions: [
              {
                id: "act-1",
                action_type: "noop",
                status: "completed",
                completed_at: "2024-06-15T12:00:00.000Z",
              },
            ],
          },
        ],
        user_actions: [
          {
            id: "ua-1",
            updated_at: "2024-03-01T08:00:00.000Z",
          },
        ],
        accounts: [
          {
            id: "acc-1",
            name: "Main",
            is_simulated: false,
            created_at: "2024-01-01T00:00:00.000Z",
            updated_at: "2024-05-01T09:00:00.000Z",
          },
        ],
        local_strategies: [
          {
            id: "strat-1",
            version: "1",
            reference_market: "USDT",
            configuration: {} as Strategy["configuration"],
            updated_at: "2024-02-01T07:00:00.000Z",
          },
        ],
      },
    }

    expect(getDebugStateLatestUpdatedAt(state)).toBe("2024-06-15T12:00:00.000Z")
  })

  it("reads user action result.updated_at", () => {
    const state: DebugState = {
      version: "1.0.0",
      debug: {
        automations: [],
        user_actions: [
          {
            id: "ua-1",
            result: {
              actual_instance: {
                updated_at: "2024-12-31T23:59:59.000Z",
                result_type: "automation",
              },
            },
          },
        ],
      },
    }
    expect(getDebugStateLatestUpdatedAt(state)).toBe("2024-12-31T23:59:59.000Z")
  })
})

describe("summarizeImportedDebugState", () => {
  it("includes latestStateUpdatedAt and section counts", () => {
    const state: DebugState = {
      version: "2.0.0",
      debug: {
        automations: [
          {
            id: "a1",
            status: "running",
            metadata: {
              name: "Bot",
              description: "",
              updated_at: "2024-01-02T00:00:00.000Z",
            },
          },
        ],
        user_actions: [{ id: "u1" }, { id: "u2" }],
        accounts: [{ id: "c1", name: "X", is_simulated: true, created_at: "" }],
        exchange_configs: [
          { id: "ex1", name: "Binance", exchange: "binance", sandboxed: false },
        ],
        local_strategies: [],
      },
    }
    const importedAt = new Date("2025-01-01T12:00:00.000Z")
    const summary = summarizeImportedDebugState(state, {
      importedAt,
      sourceLabel: "support.json",
    })

    expect(summary.version).toBe("2.0.0")
    expect(summary.sourceLabel).toBe("support.json")
    expect(summary.importedAt).toBe(importedAt)
    expect(summary.latestStateUpdatedAt).toBe("2024-01-02T00:00:00.000Z")
    expect(summary.counts).toEqual({
      automations: 1,
      userActions: 2,
      accounts: 1,
      exchangeConfigs: 1,
      strategies: 0,
    })
  })
})

describe("sanitizeDebugExportFilename", () => {
  it("sanitizes unsafe characters and ensures .json extension", () => {
    expect(sanitizeDebugExportFilename("debug state/foo.json")).toBe(
      "debug_state_foo.json",
    )
  })
})

describe("buildDebugExportFilename", () => {
  it("includes wallet suffix", () => {
    const name = buildDebugExportFilename("0x1234567890abcdef")
    expect(name).toMatch(/^debug-state-\d{8}T\d{4}-90abcdef\.json$/)
  })
})

describe("formatImportedSnapshotContents", () => {
  it("formats section counts as a comma-separated summary", () => {
    expect(
      formatImportedSnapshotContents({
        automations: 1,
        userActions: 2,
        accounts: 3,
        exchangeConfigs: 4,
        strategies: 5,
      }),
    ).toBe(
      "1 automations, 2 user actions, 3 accounts, 4 exchange configs, 5 strategies",
    )
  })
})

describe("serializeDebugStateJson / debugStateToFile", () => {
  const state: DebugState = {
    version: "1.2.3",
    debug: { automations: [], user_actions: [] },
  }

  it("serializes with the same pretty-printed JSON the download uses", () => {
    expect(serializeDebugStateJson(state)).toBe(JSON.stringify(state, null, 2))
  })

  it("packages the snapshot as an attachable JSON file (bytes match the serialization)", () => {
    const file = debugStateToFile(state, "0x1234567890abcdef")
    expect(file.mime).toBe("application/json")
    expect(file.name).toMatch(/^debug-state-\d{8}T\d{4}-90abcdef\.json$/)
    expect(new TextDecoder().decode(file.bytes)).toBe(
      serializeDebugStateJson(state),
    )
  })
})

describe("downloadDebugStateJson", () => {
  it("creates a download link for the debug state JSON", () => {
    const click = vi.fn()
    const appendChild = vi.fn()
    const removeChild = vi.fn()
    const createObjectURL = vi.fn(() => "blob:debug")
    const revokeObjectURL = vi.fn()
    const link = {
      href: "",
      download: "",
      click,
    }

    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL })
    vi.stubGlobal("document", {
      createElement: vi.fn(() => link),
      body: {
        appendChild,
        removeChild,
      },
    })

    downloadDebugStateJson(
      {
        version: "1.0.0",
        debug: { automations: [], user_actions: [] },
      },
      "snapshot.json",
    )

    expect(createObjectURL).toHaveBeenCalled()
    expect(click).toHaveBeenCalled()
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:debug")
  })
})
