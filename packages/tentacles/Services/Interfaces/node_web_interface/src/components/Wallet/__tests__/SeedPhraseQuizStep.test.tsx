import { describe, expect, it, vi } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"

import { SeedPhraseQuizStep } from "@/components/Wallet/SeedPhraseQuizStep"

vi.mock("@/lib/seed-onboarding", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/seed-onboarding")>()
  return {
    ...actual,
    pickSeedQuizPositions: () => [0, 1, 2],
  }
})

const TWELVE = Array.from({ length: 12 }, () => "abandon").join(" ")

describe("SeedPhraseQuizStep quiz inputs", () => {
  it("applies crypto-secret input attrs on quiz cells", () => {
    const markup = renderToStaticMarkup(
      <SeedPhraseQuizStep
        seed={TWELVE}
        onComplete={() => {}}
        onPrevious={() => {}}
      />,
    )

    expect(markup).toContain('spellCheck="false"')
    expect(markup).toContain('autoComplete="off"')
    expect(markup).toContain('autoCorrect="off"')
    expect(markup).toContain('autoCapitalize="none"')
  })
})
