import type { AxiosResponse } from "axios"
import { beforeEach, describe, expect, it } from "vitest"

import {
  acquireAuthLoginRedirectSuppression,
  resetAuthLoginRedirectSuppressionForTests,
} from "@/lib/auth-login-redirect-suppression"
import { shouldRedirectToLoginOn401 } from "@/lib/open-api-401-login-redirect"

function create401Response(): AxiosResponse {
  return {
    status: 401,
    data: {},
    statusText: "Unauthorized",
    headers: {},
    config: {} as AxiosResponse["config"],
  }
}

describe("shouldRedirectToLoginOn401", () => {
  beforeEach(() => {
    resetAuthLoginRedirectSuppressionForTests()
  })

  it("returns false for non-401", () => {
    const response = { ...create401Response(), status: 500 }
    expect(
      shouldRedirectToLoginOn401(response, {
        pathname: "/app/dashboard",
        isRedirectingOnAuthFailure: false,
      }),
    ).toBe(false)
  })

  it("returns true for 401 when not suppressed", () => {
    expect(
      shouldRedirectToLoginOn401(create401Response(), {
        pathname: "/app/dashboard",
        isRedirectingOnAuthFailure: false,
      }),
    ).toBe(true)
  })

  it("returns false for 401 on login page", () => {
    expect(
      shouldRedirectToLoginOn401(create401Response(), {
        pathname: "/app/login",
        isRedirectingOnAuthFailure: false,
      }),
    ).toBe(false)
  })

  it("returns false when already redirecting", () => {
    expect(
      shouldRedirectToLoginOn401(create401Response(), {
        pathname: "/app/dashboard",
        isRedirectingOnAuthFailure: true,
      }),
    ).toBe(false)
  })

  it("returns false for 401 when suppression is active", () => {
    acquireAuthLoginRedirectSuppression()
    expect(
      shouldRedirectToLoginOn401(create401Response(), {
        pathname: "/app/dashboard",
        isRedirectingOnAuthFailure: false,
      }),
    ).toBe(false)
  })
})
