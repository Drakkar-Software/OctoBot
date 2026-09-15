import { renderToStaticMarkup } from "react-dom/server"
import { beforeEach, describe, expect, it } from "vitest"

import { AuthLoginRedirectSuppressionProvider } from "@/components/Common/AuthLoginRedirectSuppressionProvider"
import {
  acquireAuthLoginRedirectSuppression,
  isAuthLoginRedirectSuppressed,
  releaseAuthLoginRedirectSuppression,
  resetAuthLoginRedirectSuppressionForTests,
} from "@/lib/auth-login-redirect-suppression"

describe("AuthLoginRedirectSuppressionProvider", () => {
  beforeEach(() => {
    resetAuthLoginRedirectSuppressionForTests()
  })

  it("wraps children (useEffect acquire/release covered by module ref-count tests)", () => {
    const markup = renderToStaticMarkup(
      <AuthLoginRedirectSuppressionProvider>
        <span id="child">ok</span>
      </AuthLoginRedirectSuppressionProvider>,
    )
    expect(markup).toContain("ok")
    acquireAuthLoginRedirectSuppression()
    expect(isAuthLoginRedirectSuppressed()).toBe(true)
    releaseAuthLoginRedirectSuppression()
  })
})
