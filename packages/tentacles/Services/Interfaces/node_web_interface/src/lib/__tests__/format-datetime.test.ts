import { describe, expect, it } from "vitest"

import { formatDateTime } from "@/lib/format-datetime"

describe("formatDateTime", () => {
  it("returns em dash for null or undefined", () => {
    expect(formatDateTime(null)).toBe("—")
    expect(formatDateTime(undefined)).toBe("—")
  })

  it("formats valid ISO timestamps", () => {
    const formatted = formatDateTime("2024-06-15T12:00:00.000Z")
    expect(formatted).not.toBe("—")
    expect(formatted).not.toBe("2024-06-15T12:00:00.000Z")
  })

  it("returns the original string for invalid dates", () => {
    expect(formatDateTime("not-a-date")).toBe("not-a-date")
  })
})
