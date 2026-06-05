import { describe, expect, it } from "vitest"

import { formatIdDisplay } from "@/lib/format-id"

describe("formatIdDisplay", () => {
  it("returns short ids unchanged", () => {
    expect(formatIdDisplay("abc12345")).toBe("abc12345")
  })

  it("truncates ids longer than the display length", () => {
    expect(formatIdDisplay("abcdefghijklmnop")).toBe("abcdefgh")
  })
})
