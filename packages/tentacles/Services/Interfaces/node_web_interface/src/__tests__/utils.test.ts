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

  it("returns string detail from FastAPI error body", () => {
    const err = new ApiError(
      { method: "POST", url: "/api/v1/setup/wallet/recover-from-seed" },
      {
        url: "/api/v1/setup/wallet/recover-from-seed",
        ok: false,
        status: 422,
        statusText: "Unprocessable Content",
        body: { detail: "Invalid seed phrase or private key" },
      },
      "Invalid seed phrase or private key",
    )
    expect(extractErrorMessage(err)).toBe("Invalid seed phrase or private key")
  })

  it("returns plain string body when detail is absent", () => {
    const err = new ApiError(
      { method: "POST", url: "/x" },
      {
        url: "/x",
        ok: false,
        status: 500,
        statusText: "Error",
        body: "Server failure text",
      },
      "Error",
    )
    expect(extractErrorMessage(err)).toBe("Server failure text")
  })

  it("falls back to ApiError message when body has no detail", () => {
    const err = new ApiError(
      { method: "POST", url: "/x" },
      {
        url: "/x",
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        body: {},
      },
      "Custom error message",
    )
    expect(extractErrorMessage(err)).toBe("Custom error message")
  })
})
