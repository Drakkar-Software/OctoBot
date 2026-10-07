import { describe, expect, it } from "vitest"

import {
  countSeedWords,
  isPassphraseLongEnough,
  isValidEvmPrivateKeyHex,
  isValidSeedPhrase,
  passphrasesMatch,
} from "@/lib/passphrase-recovery-validation"

describe("passphrase-recovery-validation", () => {
  it("counts seed words", () => {
    expect(countSeedWords("one two three")).toBe(3)
  })

  it("validates seed phrase length", () => {
    const twelve = "a b c d e f g h i j k l"
    expect(isValidSeedPhrase(twelve)).toBe(true)
    expect(isValidSeedPhrase("too short")).toBe(false)
  })

  it("validates hex private key", () => {
    const key = "0".repeat(64)
    expect(isValidEvmPrivateKeyHex(key)).toBe(true)
    expect(isValidEvmPrivateKeyHex("0x" + key)).toBe(true)
    expect(isValidEvmPrivateKeyHex("abc")).toBe(false)
  })

  it("validates passphrase length and match", () => {
    expect(isPassphraseLongEnough("12345678")).toBe(true)
    expect(isPassphraseLongEnough("short")).toBe(false)
    expect(passphrasesMatch("a", "a")).toBe(true)
    expect(passphrasesMatch("a", "b")).toBe(false)
  })
})
