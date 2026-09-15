import { beforeEach, describe, expect, it } from "vitest"

import {
  acquireAuthLoginRedirectSuppression,
  isAuthLoginRedirectSuppressed,
  releaseAuthLoginRedirectSuppression,
  resetAuthLoginRedirectSuppressionForTests,
} from "@/lib/auth-login-redirect-suppression"
import { shouldSkipLoginRedirectOn401 } from "@/lib/open-api-401-login-redirect"

describe("auth-login-redirect-suppression", () => {
  beforeEach(() => {
    resetAuthLoginRedirectSuppressionForTests()
  })

  it("starts unsuppressed", () => {
    expect(isAuthLoginRedirectSuppressed()).toBe(false)
    expect(shouldSkipLoginRedirectOn401()).toBe(false)
  })

  it("acquire and release ref-count", () => {
    acquireAuthLoginRedirectSuppression()
    expect(isAuthLoginRedirectSuppressed()).toBe(true)
    expect(shouldSkipLoginRedirectOn401()).toBe(true)

    releaseAuthLoginRedirectSuppression()
    expect(isAuthLoginRedirectSuppressed()).toBe(false)
  })

  it("supports nested acquire", () => {
    acquireAuthLoginRedirectSuppression()
    acquireAuthLoginRedirectSuppression()
    releaseAuthLoginRedirectSuppression()
    expect(isAuthLoginRedirectSuppressed()).toBe(true)
    releaseAuthLoginRedirectSuppression()
    expect(isAuthLoginRedirectSuppressed()).toBe(false)
  })

  it("does not go negative on extra release", () => {
    releaseAuthLoginRedirectSuppression()
    expect(isAuthLoginRedirectSuppressed()).toBe(false)
  })
})
