const SETUP_GENERATE_FLOW_KEY = "setup_wallet_generate_flow"

/** Session flag: user created a wallet via generate during setup (affects step counts). */
export function markSetupGenerateFlow(): void {
  sessionStorage.setItem(SETUP_GENERATE_FLOW_KEY, "true")
}

export function isSetupGenerateFlow(): boolean {
  return sessionStorage.getItem(SETUP_GENERATE_FLOW_KEY) === "true"
}

export function clearSetupGenerateFlow(): void {
  sessionStorage.removeItem(SETUP_GENERATE_FLOW_KEY)
}

export const SETUP_STEP_TOTAL_GENERATE = 5
export const SETUP_STEP_TOTAL_IMPORT = 3

export function getSetupStepTotal(): number {
  return isSetupGenerateFlow() ? SETUP_STEP_TOTAL_GENERATE : SETUP_STEP_TOTAL_IMPORT
}

export function splitSeedPhraseWords(seed: string): string[] {
  return seed.trim().split(/\s+/).filter(Boolean)
}

/** Longest token length in the BIP39 English wordlist (2048 words). */
export const BIP39_ENGLISH_MAX_WORD_LENGTH = 8

export type SeedQuizBlurResult = "neutral" | "wrong" | "correct"

/** Client-only blur validation for one quiz cell (trim + lowercase). */
export function getSeedQuizBlurResult(
  expectedWord: string,
  answer: string,
): SeedQuizBlurResult {
  const trimmed = answer.trim()
  if (!trimmed) {
    return "neutral"
  }
  if (expectedWord.toLowerCase() === trimmed.toLowerCase()) {
    return "correct"
  }
  return "wrong"
}

/** Pick `count` unique word indices in [0, wordCount). */
export function pickSeedQuizPositions(wordCount: number, count = 3): number[] {
  if (wordCount < count) {
    throw new Error(`Need at least ${count} words for the quiz`)
  }
  const positions = new Set<number>()
  while (positions.size < count) {
    positions.add(Math.floor(Math.random() * wordCount))
  }
  return [...positions].sort((a, b) => a - b)
}

/** Word indices in `positions` whose answers do not match (trim + lowercase). */
export function getSeedQuizWrongIndices(
  words: string[],
  positions: number[],
  answers: Record<number, string>,
): number[] {
  return positions.filter((index) => {
    const expected = words[index]?.toLowerCase()
    const given = answers[index]?.trim().toLowerCase()
    return !expected || !given || expected !== given
  })
}

export function areSeedQuizAnswersCorrect(
  words: string[],
  positions: number[],
  answers: Record<number, string>,
): boolean {
  return getSeedQuizWrongIndices(words, positions, answers).length === 0
}
