import { describe, expect, it, vi } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"

import { RecoverCreateWalletSection } from "@/components/Account/RecoverCreateWalletSection"

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
  useNavigate: () => vi.fn(),
}))

describe("RecoverCreateWalletSection", () => {
  it("renders create-new-wallet copy distinct from recovery", () => {
    const markup = renderToStaticMarkup(<RecoverCreateWalletSection />)
    expect(markup).toContain("Create a new wallet")
    expect(markup).toContain("Set up a new wallet")
    expect(markup).toContain("not account recovery")
  })
})
