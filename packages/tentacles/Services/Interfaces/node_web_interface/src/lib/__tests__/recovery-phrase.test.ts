import { describe, expect, it } from "vitest"

import { formatRecoveryPhraseWords } from "@/lib/recovery-phrase"

describe("formatRecoveryPhraseWords", () => {
  it("splits a normalized phrase into words", () => {
    expect(formatRecoveryPhraseWords("one two three")).toEqual(["one", "two", "three"])
  })

  it("trims extra whitespace", () => {
    expect(formatRecoveryPhraseWords("  one   two  ")).toEqual(["one", "two"])
  })
})
