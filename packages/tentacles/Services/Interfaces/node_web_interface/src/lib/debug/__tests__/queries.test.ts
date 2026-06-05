import { describe, expect, it } from "vitest"

import { getDebugQueryOptions } from "@/lib/debug/queries"

describe("getDebugQueryOptions", () => {
  it("uses the current wallet key when walletAddress is empty", () => {
    const options = getDebugQueryOptions("")
    expect(options.queryKey).toEqual(["debug", "current"])
  })

  it("includes the wallet address in the query key when provided", () => {
    const options = getDebugQueryOptions("0xabc")
    expect(options.queryKey).toEqual(["debug", "0xabc"])
  })

  it("exposes a queryFn", () => {
    expect(typeof getDebugQueryOptions().queryFn).toBe("function")
  })
})
