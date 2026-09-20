import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { PassphraseRecoveryScreen } from "@/components/Auth/PassphraseRecoveryScreen"

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, ...props }: { children: ReactNode }) => (
    <a {...props}>{children}</a>
  ),
  useNavigate: () => vi.fn(),
}))

vi.mock("@/client", () => ({
  WalletsService: {
    listWallets: vi.fn(async () => [
      { address: "0xabc", name: "Main", is_admin: true },
    ]),
  },
}))

vi.mock("@/hooks/useCustomToast", () => ({
  default: () => ({ showErrorToast: vi.fn() }),
}))

function renderScreen() {
  const client = new QueryClient()
  return renderToStaticMarkup(
    <QueryClientProvider client={client}>
      <PassphraseRecoveryScreen />
    </QueryClientProvider>,
  )
}

describe("PassphraseRecoveryScreen", () => {
  it("renders recovery copy and seed input", () => {
    const markup = renderScreen()
    expect(markup).toContain("Recover passphrase")
    expect(markup).toContain('data-testid="recovery-seed-input"')
    expect(markup).toContain("replaces your wallet passphrase")
  })
})
