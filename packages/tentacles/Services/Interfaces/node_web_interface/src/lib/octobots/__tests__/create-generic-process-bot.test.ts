import { describe, expect, it } from "vitest"

import { ApiError } from "@/client"
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
    const error = new ApiError(
      { method: "POST", url: "/api/v1/octobots/generic-process" },
      {
        url: "/api/v1/octobots/generic-process",
        ok: false,
        status: 400,
        statusText: "Bad Request",
        body: { detail: "name must not be empty" },
      },
      "Bad Request",
    )
    expect(formatCreateGenericProcessBotError(error)).toBe(
      "name must not be empty",
    )
  })

  it("uses validation array detail from ApiError", () => {
    const error = new ApiError(
      { method: "POST", url: "/api/v1/octobots/generic-process" },
      {
        url: "/api/v1/octobots/generic-process",
        ok: false,
        status: 422,
        statusText: "Unprocessable Entity",
        body: { detail: [{ msg: "Field required" }] },
      },
      "Unprocessable Entity",
    )
    expect(formatCreateGenericProcessBotError(error)).toBe("Field required")
  })

  it("falls back to a generic message", () => {
    expect(formatCreateGenericProcessBotError({})).toBe(
      "Couldn't create your OctoBot. Try again.",
    )
  })
})
