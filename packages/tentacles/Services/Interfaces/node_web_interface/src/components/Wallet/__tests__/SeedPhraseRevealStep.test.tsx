import { describe, expect, it, vi } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"

import { SeedPhraseRevealStep } from "@/components/Wallet/SeedPhraseRevealStep"

vi.mock("@/lib/use-confirm-wallet-secret-copy", () => ({
  useConfirmWalletSecretCopy: () => ({
    confirmOpen: false,
    pendingSecretType: "seed_phrase",
    requestCopy: vi.fn(),
    handleOpenChange: vi.fn(),
    handleConfirm: vi.fn(),
  }),
}))

const TWELVE_WORDS =
  "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"

describe("SeedPhraseRevealStep", () => {
  it("renders numbered seed words and offline checkbox", () => {
    const html = renderToStaticMarkup(
      <SeedPhraseRevealStep seed={TWELVE_WORDS} onContinue={vi.fn()} />,
    )
    expect(html).toContain("Save your seed phrase")
    expect(html).toContain("I saved it offline")
    expect(html).toContain("Copy seed phrase")
    expect(html).toContain("about")
    expect(html).toContain('disabled=""')
  })
})
