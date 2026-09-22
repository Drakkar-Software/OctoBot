import { describe, expect, it } from "vitest"

import { createTestApiError } from "@/lib/api-error"
import { extractErrorMessage } from "@/utils"

describe("extractErrorMessage", () => {
  it("returns message from structured auth error detail", () => {
    const err = createTestApiError(401, {
      detail: {
        code: "auth_invalid_passphrase",
        message: "Passphrase verification failed",
      },
    })
    expect(extractErrorMessage(err)).toBe("Passphrase verification failed")
  })
})
