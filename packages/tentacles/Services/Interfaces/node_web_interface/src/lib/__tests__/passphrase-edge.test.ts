import { describe, expect, it } from "vitest"

import { passphraseHasEdgeWhitespace } from "@/lib/passphrase-edge"

describe("passphraseHasEdgeWhitespace", () => {
  it("returns false for empty string", () => {
    expect(passphraseHasEdgeWhitespace("")).toBe(false)
  })

  it("returns false when no edge whitespace", () => {
    expect(passphraseHasEdgeWhitespace("demodemo")).toBe(false)
    expect(passphraseHasEdgeWhitespace("pass word")).toBe(false)
  })

  it("detects leading and trailing whitespace", () => {
    expect(passphraseHasEdgeWhitespace(" demodemo")).toBe(true)
    expect(passphraseHasEdgeWhitespace("demodemo ")).toBe(true)
    expect(passphraseHasEdgeWhitespace("\ndemodemo\n")).toBe(true)
  })
})
