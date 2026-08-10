import { describe, expect, it } from "vitest"
import {
  DEFAULT_CLOUD_SYNC_COLLECTIONS,
  MIRROR_COLLECTIONS,
  nextCollectionsOnToggle,
} from "../cloud-sync-collections"

describe("MIRROR_COLLECTIONS", () => {
  it("never includes user-accounts-auth — credentials are never mirror-eligible", () => {
    expect(MIRROR_COLLECTIONS.some((c) => c.id === "user-accounts-auth")).toBe(false)
  })

  it("has no duplicate ids", () => {
    const ids = MIRROR_COLLECTIONS.map((c) => c.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it("user-settings is not third-party eligible and defaults off", () => {
    const settings = MIRROR_COLLECTIONS.find((c) => c.id === "user-settings")
    expect(settings).toBeDefined()
    expect(settings?.thirdPartyEligible).toBe(false)
    expect(settings?.defaultEnabled).toBe(false)
  })

  it("accounts/strategies default on and are third-party eligible; user-data and trading are eligible but off by default", () => {
    const byId = Object.fromEntries(MIRROR_COLLECTIONS.map((c) => [c.id, c]))
    expect(byId["user-accounts"]).toMatchObject({ defaultEnabled: true, thirdPartyEligible: true })
    // Off by default: the node has no local reader for user-data yet — see this
    // collection's inline comment in cloud-sync-collections.ts.
    expect(byId["user-data"]).toMatchObject({ defaultEnabled: false, thirdPartyEligible: true })
    expect(byId["user-strategies"]).toMatchObject({ defaultEnabled: true, thirdPartyEligible: true })
    expect(byId["user-accounts-trading"]).toMatchObject({ defaultEnabled: false, thirdPartyEligible: true })
  })
})

describe("DEFAULT_CLOUD_SYNC_COLLECTIONS", () => {
  it("matches the backend default set exactly", () => {
    expect(DEFAULT_CLOUD_SYNC_COLLECTIONS).toEqual(["user-accounts", "user-strategies"])
  })
})

describe("nextCollectionsOnToggle", () => {
  it("adds a collection not yet present", () => {
    expect(nextCollectionsOnToggle(["user-accounts"], "user-strategies", true)).toEqual([
      "user-accounts",
      "user-strategies",
    ])
  })

  it("does not duplicate an already-present collection", () => {
    expect(nextCollectionsOnToggle(["user-accounts"], "user-accounts", true)).toEqual(["user-accounts"])
  })

  it("removes a present collection", () => {
    expect(nextCollectionsOnToggle(["user-accounts", "user-data"], "user-data", false)).toEqual([
      "user-accounts",
    ])
  })

  it("is a no-op when removing an absent collection", () => {
    expect(nextCollectionsOnToggle(["user-accounts"], "user-settings", false)).toEqual(["user-accounts"])
  })

  it("never mutates the input array", () => {
    const input = ["user-accounts"]
    const result = nextCollectionsOnToggle(input, "user-strategies", true)
    expect(input).toEqual(["user-accounts"])
    expect(result).not.toBe(input)
  })
})
