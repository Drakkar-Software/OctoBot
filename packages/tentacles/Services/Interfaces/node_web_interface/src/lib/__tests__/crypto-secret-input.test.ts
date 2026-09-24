import { describe, expect, it } from "vitest"

import {
  cryptoSecretInputProps,
  cryptoSecretTextareaProps,
} from "@/lib/crypto-secret-input"

describe("cryptoSecretInputProps", () => {
  it("disables spellcheck and mobile/autocomplete hints for crypto secrets", () => {
    expect(cryptoSecretInputProps).toEqual({
      spellCheck: false,
      autoComplete: "off",
      autoCorrect: "off",
      autoCapitalize: "none",
    })
  })

  it("reuses the same attrs for textarea surfaces", () => {
    expect(cryptoSecretTextareaProps()).toBe(cryptoSecretInputProps)
  })
})
