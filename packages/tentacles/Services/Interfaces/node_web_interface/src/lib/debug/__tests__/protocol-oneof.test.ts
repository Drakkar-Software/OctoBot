import { describe, expect, it } from "vitest"

import { resolveOneOfInstance } from "@/lib/debug/protocol-oneof"

describe("resolveOneOfInstance", () => {
  it("returns flat configuration payloads without a oneOf envelope", () => {
    const configuration = {
      action_type: "automation_stop",
      id: "auto-1",
    }
    expect(
      resolveOneOfInstance<{ action_type?: string }>(configuration)
        ?.action_type,
    ).toBe("automation_stop")
  })

  it("returns flat result payloads without a oneOf envelope", () => {
    const result = {
      updated_at: "2026-01-02T12:00:00Z",
      error_message: "automation_not_found",
      error_details: "missing automation",
      result_type: "automation",
    }
    const instance = resolveOneOfInstance<{
      updated_at?: string
      error_message?: string
      error_details?: string
    }>(result)
    expect(instance?.updated_at).toBe("2026-01-02T12:00:00Z")
    expect(instance?.error_message).toBe("automation_not_found")
    expect(instance?.error_details).toBe("missing automation")
  })

  it("prefers actual_instance on a generated oneOf wrapper", () => {
    const wrapped = {
      actual_instance: {
        action_type: "account_edit",
        configuration: { id: "acc-1" },
      },
      one_of_schemas: ["EditAccountConfiguration"],
    }
    expect(
      resolveOneOfInstance<{ action_type?: string }>(wrapped)?.action_type,
    ).toBe("account_edit")
  })
})
