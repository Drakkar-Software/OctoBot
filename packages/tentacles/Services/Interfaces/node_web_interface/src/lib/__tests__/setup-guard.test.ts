import { describe, expect, it } from "vitest"

import { getSetupRedirect } from "../setup-guard"

describe("getSetupRedirect", () => {
  // --- fresh / unconfigured node ---

  it("allows all setup routes on a fresh node", () => {
    expect(
      getSetupRedirect({
        configured: false,
        setupInProgress: false,
        loggedIn: false,
        pathname: "/setup",
      }),
    ).toBeNull()
  })

  it("allows creation step on fresh node even with setup_in_progress", () => {
    expect(
      getSetupRedirect({
        configured: true,
        setupInProgress: false,
        loggedIn: false,
        pathname: "/setup",
      }),
    ).toBe("/login")
  })

  // --- regression: the reported bug ---

  it("redirects creation step to /setup/first-bot when configured, in-progress, logged in", () => {
    // This is the exact scenario that triggered "Node is already configured":
    // wallet exists, session still has setup_in_progress, user navigated back to /setup.
    expect(
      getSetupRedirect({
        configured: true,
        setupInProgress: true,
        loggedIn: true,
        pathname: "/setup",
      }),
    ).toBe("/setup/first-bot")
  })

  // --- configured node, creation step, various states ---

  it("redirects creation step to / when configured, not in-progress, logged in", () => {
    expect(
      getSetupRedirect({
        configured: true,
        setupInProgress: false,
        loggedIn: true,
        pathname: "/setup",
      }),
    ).toBe("/")
  })

  it("redirects creation step to /login when configured and not logged in", () => {
    expect(
      getSetupRedirect({
        configured: true,
        setupInProgress: false,
        loggedIn: false,
        pathname: "/setup",
      }),
    ).toBe("/login")
  })

  it("redirects creation step to /login when configured, in-progress, but not logged in", () => {
    expect(
      getSetupRedirect({
        configured: true,
        setupInProgress: true,
        loggedIn: false,
        pathname: "/setup",
      }),
    ).toBe("/login")
  })

  // --- configured node, post-creation steps ---

  it("allows first-bot step when configured and setup is in progress", () => {
    expect(
      getSetupRedirect({
        configured: true,
        setupInProgress: true,
        loggedIn: true,
        pathname: "/setup/first-bot",
      }),
    ).toBeNull()
  })

  it("allows mobile-app step when configured and setup is in progress", () => {
    expect(
      getSetupRedirect({
        configured: true,
        setupInProgress: true,
        loggedIn: true,
        pathname: "/setup/mobile-app",
      }),
    ).toBeNull()
  })

  it("redirects post-creation step to / when configured, not in-progress, logged in", () => {
    expect(
      getSetupRedirect({
        configured: true,
        setupInProgress: false,
        loggedIn: true,
        pathname: "/setup/first-bot",
      }),
    ).toBe("/")
  })

  it("redirects post-creation step to /login when configured, not in-progress, not logged in", () => {
    expect(
      getSetupRedirect({
        configured: true,
        setupInProgress: false,
        loggedIn: false,
        pathname: "/setup/mobile-app",
      }),
    ).toBe("/login")
  })

  // --- basepath / trailing-slash robustness ---

  it("treats /setup/ (trailing slash) as the creation step", () => {
    expect(
      getSetupRedirect({
        configured: true,
        setupInProgress: true,
        loggedIn: true,
        pathname: "/setup/",
      }),
    ).toBe("/setup/first-bot")
  })

  it("treats /app/setup (with basepath prefix) as the creation step", () => {
    expect(
      getSetupRedirect({
        configured: true,
        setupInProgress: true,
        loggedIn: true,
        pathname: "/app/setup",
      }),
    ).toBe("/setup/first-bot")
  })

  it("treats /app/setup/ (basepath + trailing slash) as the creation step", () => {
    expect(
      getSetupRedirect({
        configured: true,
        setupInProgress: true,
        loggedIn: true,
        pathname: "/app/setup/",
      }),
    ).toBe("/setup/first-bot")
  })
})
