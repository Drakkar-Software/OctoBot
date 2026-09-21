import { afterEach, describe, expect, it, vi } from "vitest"

import {
  areSeedQuizAnswersCorrect,
  clearSetupGenerateFlow,
  isSetupGenerateFlow,
  markSetupGenerateFlow,
  pickSeedQuizPositions,
  splitSeedPhraseWords,
} from "@/lib/seed-onboarding"

const sessionStorageStore: Record<string, string> = {}
const sessionStorageMock = {
  getItem: (key: string) => sessionStorageStore[key] ?? null,
  setItem: (key: string, value: string) => {
    sessionStorageStore[key] = value
  },
  removeItem: (key: string) => {
    delete sessionStorageStore[key]
  },
  clear: () => {
    Object.keys(sessionStorageStore).forEach((key) => {
      delete sessionStorageStore[key]
    })
  },
}

vi.stubGlobal("sessionStorage", sessionStorageMock)

afterEach(() => {
  sessionStorageMock.clear()
})

describe("setup generate flow session flag", () => {
  it("tracks generate onboarding in sessionStorage", () => {
    expect(isSetupGenerateFlow()).toBe(false)
    markSetupGenerateFlow()
    expect(isSetupGenerateFlow()).toBe(true)
    clearSetupGenerateFlow()
    expect(isSetupGenerateFlow()).toBe(false)
  })
})

describe("splitSeedPhraseWords", () => {
  it("splits a normalized BIP39 phrase", () => {
    expect(splitSeedPhraseWords("abandon abandon abandon")).toEqual([
      "abandon",
      "abandon",
      "abandon",
    ])
  })
})

describe("pickSeedQuizPositions", () => {
  it("returns three unique sorted indices", () => {
    let n = 0
    vi.spyOn(Math, "random").mockImplementation(() => {
      n += 1
      return (n * 0.17) % 1
    })
    const positions = pickSeedQuizPositions(12, 3)
    expect(positions).toHaveLength(3)
    expect(new Set(positions).size).toBe(3)
    expect(positions).toEqual([...positions].sort((a, b) => a - b))
    vi.restoreAllMocks()
  })
})

describe("areSeedQuizAnswersCorrect", () => {
  const words = ["one", "two", "three", "four"]

  it("accepts matching answers case-insensitively", () => {
    expect(
      areSeedQuizAnswersCorrect(words, [0, 2], { 0: "ONE", 2: "three" }),
    ).toBe(true)
  })

  it("rejects wrong answers", () => {
    expect(
      areSeedQuizAnswersCorrect(words, [1], { 1: "wrong" }),
    ).toBe(false)
  })
})
