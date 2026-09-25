import { describe, expect, it } from "vitest"

import { ApiError } from "@/client/core/ApiError"
import {
  formatRateLimitUnblockLocalTime,
  parseRateLimitDetail,
} from "@/lib/parse-rate-limit-api-error"

function makeRateLimitApiError(detail: unknown): ApiError {
  return new ApiError(
    { method: "POST", url: "/x" },
    {
      url: "/x",
      ok: false,
      status: 429,
      statusText: "Too Many Requests",
      body: { detail },
    },
    "Too Many Requests",
  )
}

describe("parseRateLimitDetail", () => {
  it("parses message and unblock_at", () => {
    const error = makeRateLimitApiError({
      message: "Too many login attempts. Try again later.",
      unblock_at: 1_700_000_000,
    })
    expect(parseRateLimitDetail(error)).toEqual({
      message: "Too many login attempts. Try again later.",
      unblockAt: 1_700_000_000,
    })
  })

  it("returns null for string detail", () => {
    const error = makeRateLimitApiError("Too many attempts")
    expect(parseRateLimitDetail(error)).toBeNull()
  })

  it("returns null when unblock_at is missing or invalid", () => {
    expect(
      parseRateLimitDetail(
        makeRateLimitApiError({ message: "Limited", unblock_at: "bad" }),
      ),
    ).toBeNull()
    expect(
      parseRateLimitDetail(makeRateLimitApiError({ message: "Limited" })),
    ).toBeNull()
  })
})

describe("formatRateLimitUnblockLocalTime", () => {
  it("formats a fixed epoch in en-US", () => {
    const unblockAt = 1_704_067_200
    const text = formatRateLimitUnblockLocalTime(unblockAt, "en-US")
    expect(text).toMatch(/^Try again after /)
    expect(text.endsWith(".")).toBe(true)
    expect(text).toContain(":")
  })
})
