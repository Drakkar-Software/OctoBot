import { describe, expect, it } from "vitest"

import { getSetupRedirect, isPreWalletSetupRoute } from "@/lib/setup-guard"

describe("isPreWalletSetupRoute", () => {
  it("matches wallet and welcome routes", () => {
    expect(isPreWalletSetupRoute("/setup")).toBe(true)
    expect(isPreWalletSetupRoute("/setup/")).toBe(true)
    expect(isPreWalletSetupRoute("/setup/welcome")).toBe(true)
    expect(isPreWalletSetupRoute("/app/setup/welcome")).toBe(true)
  })

  it("does not match post-wallet routes", () => {
    expect(isPreWalletSetupRoute("/setup/connect")).toBe(false)
    expect(isPreWalletSetupRoute("/setup/first-bot")).toBe(false)
  })
})

describe("getSetupRedirect", () => {
  it("allows all setup routes when unconfigured", () => {
    expect(
      getSetupRedirect({
        configured: false,
        setupInProgress: false,
        loggedIn: false,
        pathname: "/setup/welcome",
      }),
    ).toBeNull()
    expect(
      getSetupRedirect({
        configured: false,
        setupInProgress: false,
        loggedIn: false,
        pathname: "/setup/connect",
      }),
    ).toBeNull()
  })

  it("redirects configured wallet routes to connect during setup", () => {
    expect(
      getSetupRedirect({
        configured: true,
        setupInProgress: true,
        loggedIn: true,
        pathname: "/setup",
      }),
    ).toBe("/setup/connect")
    expect(
      getSetupRedirect({
        configured: true,
        setupInProgress: true,
        loggedIn: true,
        pathname: "/setup/welcome",
      }),
    ).toBe("/setup/connect")
  })

  it("allows connect and first-bot only during setup", () => {
    expect(
      getSetupRedirect({
        configured: true,
        setupInProgress: true,
        loggedIn: true,
        pathname: "/setup/connect",
      }),
    ).toBeNull()
    expect(
      getSetupRedirect({
        configured: true,
        setupInProgress: false,
        loggedIn: true,
        pathname: "/setup/connect",
      }),
    ).toBe("/")
  })
})
