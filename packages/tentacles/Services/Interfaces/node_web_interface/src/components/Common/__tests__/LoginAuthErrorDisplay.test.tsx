import { describe, expect, it } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"

import { LoginAuthErrorDisplay } from "@/components/Common/LoginAuthErrorDisplay"
import { API_AUTH_ERROR_CODES } from "@/lib/auth-error-codes"
import { applyLoginAuthPresentation } from "@/lib/auth-error-messages"

describe("LoginAuthErrorDisplay", () => {
  it("renders nothing when presentation is null", () => {
    const html = renderToStaticMarkup(
      <LoginAuthErrorDisplay presentation={null} />,
    )
    expect(html).toBe("")
  })

  it("renders error and tips when guidance is present", () => {
    const presentation = applyLoginAuthPresentation(
      API_AUTH_ERROR_CODES.AUTH_INVALID_PASSPHRASE,
      { multiWallet: true },
      false,
    )
    const html = renderToStaticMarkup(
      <LoginAuthErrorDisplay presentation={presentation} />,
    )
    expect(html).toContain('data-testid="login-auth-error"')
    expect(html).toContain("Wrong passphrase")
    expect(html).toContain('data-testid="login-auth-tips"')
    expect(html).toContain("Tip")
    expect(html.match(/<li>/g)?.length).toBe(presentation.guidance.length)
  })

  it("omits tips when guidance is empty", () => {
    const presentation = applyLoginAuthPresentation(
      API_AUTH_ERROR_CODES.AUTH_PASSPHRASE_REQUIRED,
      { multiWallet: false },
      false,
    )
    const html = renderToStaticMarkup(
      <LoginAuthErrorDisplay presentation={presentation} />,
    )
    expect(html).toContain('data-testid="login-auth-error"')
    expect(html).not.toContain('data-testid="login-auth-tips"')
  })
})
