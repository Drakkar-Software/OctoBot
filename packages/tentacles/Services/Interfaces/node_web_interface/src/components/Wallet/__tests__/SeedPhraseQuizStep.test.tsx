import { describe, expect, it, vi } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"

import { SeedPhraseQuizStep } from "@/components/Wallet/SeedPhraseQuizStep"

vi.mock("@/lib/seed-onboarding", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/seed-onboarding")>()
  return {
    ...actual,
    pickSeedQuizPositions: () => [0, 5, 11],
  }
})

const TWELVE_WORDS =
  "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"

describe("SeedPhraseQuizStep", () => {
  it("renders three word prompts and Previous", () => {
    const html = renderToStaticMarkup(
      <SeedPhraseQuizStep
        seed={TWELVE_WORDS}
        onComplete={vi.fn()}
        onPrevious={vi.fn()}
      />,
    )
    expect(html).toContain("Confirm your seed phrase")
    expect(html).toContain("Word #1")
    expect(html).toContain("Word #6")
    expect(html).toContain("Word #12")
    expect(html).toContain("Previous")
  })
})
