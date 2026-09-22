import { describe, expect, it } from "vitest"

import { createTestApiError } from "@/lib/api-error"
import {
  buildCreateGenericProcessBotRequestBody,
  formatCreateGenericProcessBotError,
  validateCreateGenericProcessBotName,
} from "../create-generic-process-bot"

describe("validateCreateGenericProcessBotName", () => {
  it("rejects empty and whitespace-only names", () => {
    expect(validateCreateGenericProcessBotName("")).toEqual({
      valid: false,
      message: "Enter a name for your OctoBot.",
    })
    expect(validateCreateGenericProcessBotName("   ")).toEqual({
      valid: false,
      message: "Enter a name for your OctoBot.",
    })
  })

  it("accepts trimmed non-empty names", () => {
    expect(validateCreateGenericProcessBotName("  My bot  ")).toEqual({
      valid: true,
      trimmedName: "My bot",
    })
  })
})

describe("buildCreateGenericProcessBotRequestBody", () => {
  it("builds the API request body", () => {
    expect(buildCreateGenericProcessBotRequestBody("Lab bot")).toEqual({
      name: "Lab bot",
    })
  })
})

describe("formatCreateGenericProcessBotError", () => {
  it("uses string detail from ApiError", () => {
    const error = createTestApiError(400, { detail: "name must not be empty" })
    expect(formatCreateGenericProcessBotError(error)).toBe(
      "name must not be empty",
    )
  })

  it("uses validation array detail from ApiError", () => {
    const error = createTestApiError(422, {
      detail: [{ msg: "Field required" }],
    })
    expect(formatCreateGenericProcessBotError(error)).toBe("Field required")
  })

  it("falls back to a generic message", () => {
    expect(formatCreateGenericProcessBotError({})).toBe(
      "Couldn't create your OctoBot. Try again.",
    )
  })
})
