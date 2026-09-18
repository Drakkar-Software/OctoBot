import { describe, expect, it } from "vitest"

import { ApiError } from "@/client"
import { extractErrorMessage } from "@/utils"

describe("extractErrorMessage", () => {
  it("returns message from structured auth error detail", () => {
    const err = new ApiError(
      { method: "GET", url: "/api/v1/login/test" },
      {
        url: "/api/v1/login/test",
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        body: {
          detail: {
            code: "auth_invalid_passphrase",
            message: "Passphrase verification failed",
          },
        },
      },
      "Unauthorized",
    )
    expect(extractErrorMessage(err)).toBe("Passphrase verification failed")
  })
})
