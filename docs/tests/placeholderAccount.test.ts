import { describe, expect, it } from "vitest"
import {
  isExpectedPlaceholderRejection,
  PLACEHOLDER_ACCOUNT_ID,
  usedGenuinePlaceholder,
} from "../src/components/demo/lib/placeholderAccount"

// Regression coverage for the exact bug reported: a genuinely unauthorized
// connection (accounts.list() 403s) got mislabeled with "expected: the node
// validated the queued action and correctly rejected the placeholder" —
// text that only makes sense for a real, successful, empty account list.

describe("usedGenuinePlaceholder", () => {
  it("true: the placeholder id was used AND the list call genuinely succeeded (a real node with zero accounts)", () => {
    expect(
      usedGenuinePlaceholder({
        accountId: PLACEHOLDER_ACCOUNT_ID,
        listSucceeded: true,
      }),
    ).toBe(true)
  })

  it("false: the placeholder id was used but the list call never succeeded — THE regression scenario (e.g. a 403 on accounts.list())", () => {
    expect(
      usedGenuinePlaceholder({
        accountId: PLACEHOLDER_ACCOUNT_ID,
        listSucceeded: false,
      }),
    ).toBe(false)
  })

  it("false: a real account id was used, regardless of list status", () => {
    expect(
      usedGenuinePlaceholder({ accountId: "acc-real-1", listSucceeded: true }),
    ).toBe(false)
    expect(
      usedGenuinePlaceholder({
        accountId: "acc-real-1",
        listSucceeded: false,
      }),
    ).toBe(false)
  })
})

describe("isExpectedPlaceholderRejection", () => {
  it("true: placeholder was genuinely used AND the node rejected the queued action (action_failed)", () => {
    expect(
      isExpectedPlaceholderRejection({
        usedPlaceholder: true,
        errorCode: "action_failed",
      }),
    ).toBe(true)
  })

  it("false: placeholder was used but the failure was 'unauthorized' — THE reported bug (a 403 mislabeled as the expected placeholder rejection)", () => {
    expect(
      isExpectedPlaceholderRejection({
        usedPlaceholder: true,
        errorCode: "unauthorized",
      }),
    ).toBe(false)
  })

  it("false for every other error code while a placeholder was used (connection failures, conflicts, timeouts)", () => {
    for (const code of [
      "unreachable",
      "timeout",
      "aborted",
      "conflict",
      "http",
      undefined,
    ]) {
      expect(
        isExpectedPlaceholderRejection({
          usedPlaceholder: true,
          errorCode: code,
        }),
      ).toBe(false)
    }
  })

  it("false when the placeholder was never used, even if the error code is action_failed", () => {
    expect(
      isExpectedPlaceholderRejection({
        usedPlaceholder: false,
        errorCode: "action_failed",
      }),
    ).toBe(false)
  })
})
