import { describe, expect, it } from "vitest"

import { API_AUTH_ERROR_CODES } from "@/lib/auth-error-codes"
import { parseAuthErrorCodeFromBody } from "@/lib/parse-auth-api-error"

describe("parseAuthErrorCodeFromBody", () => {
  it("reads nested FastAPI detail.code", () => {
    expect(
      parseAuthErrorCodeFromBody({
        detail: { code: API_AUTH_ERROR_CODES.AUTH_INVALID_PASSPHRASE },
      }),
    ).toBe(API_AUTH_ERROR_CODES.AUTH_INVALID_PASSPHRASE)
  })

  it("returns null for unknown codes", () => {
    expect(parseAuthErrorCodeFromBody({ detail: { code: "other" } })).toBeNull()
  })
})
