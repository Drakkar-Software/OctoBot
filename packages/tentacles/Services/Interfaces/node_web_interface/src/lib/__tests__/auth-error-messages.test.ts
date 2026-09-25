import { describe, expect, it } from "vitest"

import { ApiError } from "@/client/core/ApiError"
import {
  API_AUTH_ERROR_CODES,
  CLIENT_AUTH_ERROR_CODES,
} from "@/lib/auth-error-codes"
import {
  applyLoginAuthPresentation,
  getAuthErrorPresentation,
  resolveLoginAuthPresentation,
  resolveLoginFormAuthError,
  shouldSuppressLoginErrorToast,
} from "@/lib/auth-error-messages"

describe("applyLoginAuthPresentation", () => {
  it("single-wallet invalid passphrase has no tips", () => {
    const presentation = applyLoginAuthPresentation(
      API_AUTH_ERROR_CODES.AUTH_INVALID_PASSPHRASE,
      { multiWallet: false },
      false,
    )
    expect(presentation.guidance).toHaveLength(0)
    expect(JSON.stringify(presentation)).not.toMatch(/password manager/i)
  })

  it("multi-wallet invalid passphrase has one wallet tip", () => {
    const presentation = applyLoginAuthPresentation(
      API_AUTH_ERROR_CODES.AUTH_INVALID_PASSPHRASE,
      { multiWallet: true },
      false,
    )
    expect(presentation.guidance).toEqual([
      "Make sure you chose the right wallet.",
    ])
  })

  it("edge whitespace has one short tip and updated explanation", () => {
    const presentation = applyLoginAuthPresentation(
      API_AUTH_ERROR_CODES.AUTH_INVALID_PASSPHRASE,
      { multiWallet: false },
      true,
    )
    expect(presentation.guidance).toHaveLength(1)
    expect(presentation.guidance[0]).toMatch(/Remove those spaces/i)
    expect(presentation.explanation).toMatch(/start or end/i)
  })

  it("wallet not found has at most two tips", () => {
    const presentation = applyLoginAuthPresentation(
      API_AUTH_ERROR_CODES.AUTH_WALLET_NOT_FOUND,
      { multiWallet: false },
      false,
    )
    expect(presentation.guidance).toHaveLength(2)
  })
})

describe("resolveLoginAuthPresentation", () => {
  it("maps invalid passphrase API code with no tips on single-wallet", () => {
    const error = new ApiError(
      { method: "GET", url: "/login/test" },
      {
        url: "/login/test",
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        body: {
          detail: {
            code: API_AUTH_ERROR_CODES.AUTH_INVALID_PASSPHRASE,
            message: "Passphrase verification failed",
          },
        },
      },
      "Unauthorized",
    )
    const presentation = resolveLoginAuthPresentation(error, "pw", {
      multiWallet: false,
    })
    expect(presentation.title).toBe("Wrong passphrase")
    expect(presentation.explanation).toContain("Try again")
    expect(presentation.guidance).toHaveLength(0)
  })

  it("adds whitespace tip when passphrase has edge spaces", () => {
    const error = new ApiError(
      { method: "GET", url: "/login/test" },
      {
        url: "/login/test",
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        body: {
          detail: { code: API_AUTH_ERROR_CODES.AUTH_INVALID_PASSPHRASE },
        },
      },
      "Unauthorized",
    )
    const presentation = resolveLoginAuthPresentation(error, " demodemo", {
      multiWallet: false,
    })
    expect(presentation.guidance).toHaveLength(1)
    expect(presentation.guidance[0]).toMatch(/Remove those spaces/i)
  })

  it("returns empty guidance for passphrase required code", () => {
    const error = new ApiError(
      { method: "GET", url: "/login/test" },
      {
        url: "/login/test",
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        body: {
          detail: { code: API_AUTH_ERROR_CODES.AUTH_PASSPHRASE_REQUIRED },
        },
      },
      "Unauthorized",
    )
    const presentation = resolveLoginAuthPresentation(error, "")
    expect(presentation.guidance).toHaveLength(0)
  })

  it("maps non-ApiError to device storage presentation", () => {
    const presentation = resolveLoginAuthPresentation(new Error("idb"), "pw")
    expect(presentation.title).toBe("Can't save sign-in")
    expect(presentation.guidance).toHaveLength(1)
  })

  it("maps unknown ApiError status to network presentation", () => {
    const error = new ApiError(
      { method: "GET", url: "/x" },
      {
        url: "/x",
        ok: false,
        status: 500,
        statusText: "Error",
        body: {},
      },
      "Error",
    )
    const presentation = resolveLoginAuthPresentation(error, "pw")
    expect(presentation.title).toBe("Can't connect")
    expect(presentation.guidance).toHaveLength(1)
  })

  it("maps 429 to login rate limit presentation", () => {
    const error = new ApiError(
      { method: "GET", url: "/login/test" },
      {
        url: "/login/test",
        ok: false,
        status: 429,
        statusText: "Too Many Requests",
        body: { detail: "Too many login attempts. Try again later." },
      },
      "Too Many Requests",
    )
    const presentation = resolveLoginAuthPresentation(error, "pw")
    expect(presentation.title).toBe("Too many login attempts")
    expect(presentation.explanation).toMatch(/Try again later/i)
    expect(presentation.guidance).toHaveLength(0)
  })
})

describe("shouldSuppressLoginErrorToast", () => {
  it("suppresses 401 auth errors", () => {
    const error = new ApiError(
      { method: "GET", url: "/login/test" },
      {
        url: "/login/test",
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        body: {
          detail: { code: API_AUTH_ERROR_CODES.AUTH_INVALID_PASSPHRASE },
        },
      },
      "Unauthorized",
    )
    expect(shouldSuppressLoginErrorToast(error)).toBe(true)
  })

  it("does not suppress generic 503", () => {
    const error = new ApiError(
      { method: "GET", url: "/x" },
      {
        url: "/x",
        ok: false,
        status: 503,
        statusText: "Unavailable",
        body: { detail: { code: "other" } },
      },
      "Unavailable",
    )
    expect(shouldSuppressLoginErrorToast(error)).toBe(false)
  })

  it("suppresses node not configured 503", () => {
    const error = new ApiError(
      { method: "GET", url: "/x" },
      {
        url: "/x",
        ok: false,
        status: 503,
        statusText: "Unavailable",
        body: {
          detail: { code: API_AUTH_ERROR_CODES.AUTH_NODE_NOT_CONFIGURED },
        },
      },
      "Unavailable",
    )
    expect(shouldSuppressLoginErrorToast(error)).toBe(true)
  })

  it("suppresses 429 rate limit", () => {
    const error = new ApiError(
      { method: "GET", url: "/login/test" },
      {
        url: "/login/test",
        ok: false,
        status: 429,
        statusText: "Too Many Requests",
        body: { detail: "Too many login attempts. Try again later." },
      },
      "Too Many Requests",
    )
    expect(shouldSuppressLoginErrorToast(error)).toBe(true)
  })
})

describe("resolveLoginFormAuthError", () => {
  it("maps wallet not found API code", () => {
    const error = new ApiError(
      { method: "GET", url: "/login/test" },
      {
        url: "/login/test",
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        body: {
          detail: { code: API_AUTH_ERROR_CODES.AUTH_WALLET_NOT_FOUND },
        },
      },
      "Unauthorized",
    )
    const message = resolveLoginFormAuthError(error, "pw")
    expect(message).toContain("Wallet not found here")
    expect(message).toContain("same node address")
  })
})

describe("getAuthErrorPresentation", () => {
  it("session expired copy is short and has no guidance bullets", () => {
    const presentation = getAuthErrorPresentation(
      CLIENT_AUTH_ERROR_CODES.SESSION_CLEARED,
    )
    expect(presentation.title).toBe("Session expired")
    expect(presentation.explanation).toMatch(/sign in again/i)
    expect(presentation.guidance).toHaveLength(0)
  })
})
