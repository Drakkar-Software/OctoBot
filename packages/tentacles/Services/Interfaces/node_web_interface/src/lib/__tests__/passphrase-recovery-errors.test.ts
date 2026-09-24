import { describe, expect, it } from "vitest"

import { ApiError } from "@/client"
import { resolveRecoverSeedSubmitError } from "@/lib/passphrase-recovery-errors"

function makeApiError(status: number, body: unknown, message: string): ApiError {
  return new ApiError(
    { method: "POST", url: "/api/v1/setup/wallet/recover-from-seed" },
    {
      url: "/api/v1/setup/wallet/recover-from-seed",
      ok: false,
      status,
      statusText: "Error",
      body,
    },
    message,
  )
}

describe("resolveRecoverSeedSubmitError", () => {
  it("maps 401 to wallet mismatch copy", () => {
    const result = resolveRecoverSeedSubmitError(
      makeApiError(401, { detail: "mismatch" }, "Unauthorized"),
    )
    expect(result.unavailable).toBe(false)
    expect(result.message).toBe(
      "That seed phrase or private key does not match this wallet.",
    )
  })

  it("maps 422 to unverified seed copy", () => {
    const result = resolveRecoverSeedSubmitError(
      makeApiError(
        422,
        { detail: "Invalid seed phrase or private key" },
        "Invalid seed phrase or private key",
      ),
    )
    expect(result.unavailable).toBe(false)
    expect(result.message).toContain("could not be verified")
  })

  it("maps 404 to wallet not on node copy", () => {
    const result = resolveRecoverSeedSubmitError(
      makeApiError(404, { detail: "Wallet not found" }, "Not Found"),
    )
    expect(result.message).toBe("This wallet is not set up on this node.")
  })

  it("maps 429 to rate limit copy", () => {
    const result = resolveRecoverSeedSubmitError(
      makeApiError(429, { detail: "rate limited" }, "Too Many Requests"),
    )
    expect(result.message).toMatch(/Too many attempts/)
  })

  it("maps 503 with unavailable flag and server detail", () => {
    const result = resolveRecoverSeedSubmitError(
      makeApiError(503, { detail: "read-only" }, "read-only"),
    )
    expect(result.unavailable).toBe(true)
    expect(result.message).toBe("read-only")
  })

  it("maps non-ApiError to generic copy", () => {
    const result = resolveRecoverSeedSubmitError(new Error("network"))
    expect(result).toEqual({
      message: "Something went wrong.",
      unavailable: false,
    })
  })
})
