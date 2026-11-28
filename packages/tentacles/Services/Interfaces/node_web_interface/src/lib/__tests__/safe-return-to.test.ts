import { describe, expect, it } from "vitest"

import {
  loginRedirectHref,
  resolvePostLoginDestination,
  safeReturnTo,
} from "@/lib/safe-return-to"

describe("safeReturnTo", () => {
  it.each([
    ["/app/octobots/new", "/octobots/new"],
    ["/octobots/new", "/octobots/new"],
    ["/app/settings", "/settings"],
    ["/app/settings/", "/settings"],
    ["/settings", "/settings"],
    ["/app/settings/connect", "/settings/connect"],
    ["/settings/connect", "/settings/connect"],
    ["/app/settings/connect/", "/settings/connect"],
  ])("maps %s to %s", (raw, expected) => {
    expect(safeReturnTo(raw)).toBe(expected)
  })

  it.each([
    "https://evil.example/app/settings",
    "//evil/app/settings",
    "/app/settings?x=1",
    "/unknown",
    "/app/debug",
    "/app/octobots",
  ])("rejects %s", (raw) => {
    expect(safeReturnTo(raw)).toBeNull()
  })
})

describe("resolvePostLoginDestination", () => {
  it("uses safe router path when returnTo is valid", () => {
    expect(resolvePostLoginDestination("/app/settings")).toBe("/settings")
    expect(resolvePostLoginDestination("/app/settings/connect")).toBe(
      "/settings/connect",
    )
  })

  it("falls back to home when returnTo is missing or invalid", () => {
    expect(resolvePostLoginDestination(undefined)).toBe("/")
    expect(resolvePostLoginDestination("//evil")).toBe("/")
  })
})

describe("loginRedirectHref", () => {
  it("includes returnTo for allowlisted handoff paths", () => {
    expect(loginRedirectHref("/app/settings/connect")).toBe(
      "/app/login?returnTo=%2Fapp%2Fsettings%2Fconnect",
    )
    expect(loginRedirectHref("/app/settings")).toBe(
      "/app/login?returnTo=%2Fapp%2Fsettings",
    )
    expect(loginRedirectHref("/app/octobots/new")).toBe(
      "/app/login?returnTo=%2Fapp%2Foctobots%2Fnew",
    )
  })

  it("returns bare login when path is not allowlisted", () => {
    expect(loginRedirectHref("/app/octobots")).toBe("/app/login")
    expect(loginRedirectHref("/app/debug")).toBe("/app/login")
  })
})