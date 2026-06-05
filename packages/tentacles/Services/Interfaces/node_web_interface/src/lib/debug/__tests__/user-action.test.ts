import { describe, expect, it } from "vitest"

import type { UserAction } from "@/client"
import {
  getConfigurationActionType,
  getUserActionResultErrorDetails,
  getUserActionResultErrorMessage,
  getUserActionResultField,
  getUserActionUpdatedAt,
  validateUserActionJson,
} from "@/lib/debug/user-action"

describe("getConfigurationActionType", () => {
  it("reads action_type from flat configuration payloads", () => {
    expect(
      getConfigurationActionType({
        action_type: "automation_stop",
        id: "auto-1",
      } as UserAction["configuration"]),
    ).toBe("automation_stop")
  })
})

describe("getUserActionResultField", () => {
  it("returns em dash when the field is missing", () => {
    expect(getUserActionResultField(undefined, "error_message")).toBe("—")
  })

  it("reads fields from flat result payloads", () => {
    expect(
      getUserActionResultField(
        {
          error_message: "not_found",
          error_details: "missing resource",
        } as UserAction["result"],
        "error_details",
      ),
    ).toBe("missing resource")
  })
})

describe("getUserActionResultErrorMessage", () => {
  it("delegates to getUserActionResultField", () => {
    expect(
      getUserActionResultErrorMessage({ error_message: "failed" } as UserAction["result"]),
    ).toBe("failed")
  })
})

describe("getUserActionResultErrorDetails", () => {
  it("delegates to getUserActionResultField", () => {
    expect(
      getUserActionResultErrorDetails({ error_details: "stack trace" } as UserAction["result"]),
    ).toBe("stack trace")
  })
})

describe("getUserActionUpdatedAt", () => {
  it("prefers result.updated_at over user action timestamps", () => {
    expect(
      getUserActionUpdatedAt({
        id: "ua-1",
        updated_at: "2024-01-01T00:00:00.000Z",
        created_at: "2023-12-01T00:00:00.000Z",
        result: { updated_at: "2024-06-01T00:00:00.000Z" } as UserAction["result"],
      }),
    ).toBe("2024-06-01T00:00:00.000Z")
  })
})

describe("validateUserActionJson", () => {
  it("accepts valid user action JSON", () => {
    expect(
      validateUserActionJson(JSON.stringify({ id: "ua-1", configuration: {} })),
    ).toBeNull()
  })

  it("rejects empty input", () => {
    expect(validateUserActionJson("   ")).toBe("JSON cannot be empty")
  })

  it("requires a string id field", () => {
    expect(validateUserActionJson(JSON.stringify({ configuration: {} }))).toBe(
      'Payload must include a string "id" field',
    )
  })
})
