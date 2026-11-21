import { describe, expect, it } from "vitest"

import type { MobileUiStatusResponse } from "@/client"
import {
  canOpenFirstRunMobileOnboarding,
  evaluateFirstRunWelcomeTick,
  getFirstRunFailureMessage,
  isFirstRunFailureState,
  resolveFirstRunWelcomeMobileAction,
  shouldPollFirstRunMobileUi,
  shouldResumeFirstRunDownload,
} from "@/lib/first-run-mobile-ui"

function status(
  overrides: Partial<MobileUiStatusResponse> &
    Pick<MobileUiStatusResponse, "state">,
): MobileUiStatusResponse {
  return {
    installed_version: null,
    latest_version: null,
    update_available: false,
    last_error: null,
    ...overrides,
  }
}

const notDownloading = { downloadInProgress: false }
const downloading = { downloadInProgress: true }

describe("first-run-mobile-ui", () => {
  describe("shouldPollFirstRunMobileUi", () => {
    it("polls only while installing when not downloading", () => {
      expect(
        shouldPollFirstRunMobileUi(status({ state: "installing" }), notDownloading),
      ).toBe(true)
      expect(
        shouldPollFirstRunMobileUi(status({ state: "ready" }), notDownloading),
      ).toBe(false)
      expect(
        shouldPollFirstRunMobileUi(status({ state: "not_installed" }), notDownloading),
      ).toBe(false)
    })

    it("polls for any state while welcome download is in progress", () => {
      expect(
        shouldPollFirstRunMobileUi(status({ state: "not_installed" }), downloading),
      ).toBe(true)
      expect(
        shouldPollFirstRunMobileUi(status({ state: "ready" }), downloading),
      ).toBe(true)
      expect(
        shouldPollFirstRunMobileUi(status({ state: "installing" }), downloading),
      ).toBe(true)
    })
  })

  describe("shouldResumeFirstRunDownload", () => {
    it("resumes when choose phase sees installing on server", () => {
      expect(
        shouldResumeFirstRunDownload("choose", status({ state: "installing" })),
      ).toBe(true)
      expect(
        shouldResumeFirstRunDownload("downloading", status({ state: "installing" })),
      ).toBe(false)
    })
  })

  describe("resolveFirstRunWelcomeMobileAction", () => {
    it("maps phases and status to primary CTA", () => {
      expect(
        resolveFirstRunWelcomeMobileAction(
          "downloading",
          status({ state: "installing" }),
          false,
        ),
      ).toBe("busy")
      expect(
        resolveFirstRunWelcomeMobileAction(
          "failed",
          status({ state: "error" }),
          false,
        ),
      ).toBe("retry")
      expect(
        resolveFirstRunWelcomeMobileAction(
          "choose",
          status({ state: "ready" }),
          false,
        ),
      ).toBe("open")
      expect(
        resolveFirstRunWelcomeMobileAction(
          "choose",
          status({ state: "not_installed" }),
          false,
        ),
      ).toBe("download")
      expect(
        resolveFirstRunWelcomeMobileAction(
          "choose",
          status({ state: "installing" }),
          false,
        ),
      ).toBe("busy")
    })
  })

  it("treats not_configured and error as failure", () => {
    expect(isFirstRunFailureState(status({ state: "not_configured" }))).toBe(
      true,
    )
    expect(isFirstRunFailureState(status({ state: "error" }))).toBe(true)
    expect(isFirstRunFailureState(status({ state: "installing" }))).toBe(false)
  })

  it("opens mobile only when ready and node unconfigured", () => {
    expect(
      canOpenFirstRunMobileOnboarding(status({ state: "ready" }), false),
    ).toBe(true)
    expect(
      canOpenFirstRunMobileOnboarding(status({ state: "ready" }), true),
    ).toBe(false)
    expect(
      canOpenFirstRunMobileOnboarding(status({ state: "installing" }), false),
    ).toBe(false)
  })

  it("returns actionable message for not_configured", () => {
    expect(getFirstRunFailureMessage(status({ state: "not_configured" }))).toBe(
      "OctoBot browser app download is not configured on this node yet.",
    )
  })

  it("welcome tick: configured while installing → login, not open_mobile", () => {
    expect(
      evaluateFirstRunWelcomeTick(
        status({ state: "installing" }),
        true,
        false,
        "downloading",
      ),
    ).toEqual({ action: "login" })
  })

  it("welcome tick: ready and unconfigured → open_mobile when downloading", () => {
    expect(
      evaluateFirstRunWelcomeTick(
        status({ state: "ready" }),
        false,
        false,
        "downloading",
      ),
    ).toEqual({ action: "open_mobile" })
  })

  it("welcome tick: ready on choose phase does not open mobile", () => {
    expect(
      evaluateFirstRunWelcomeTick(
        status({ state: "ready" }),
        false,
        false,
        "choose",
      ),
    ).toEqual({ action: "continue" })
  })

  it("welcome tick: first-run 409 → login", () => {
    expect(
      evaluateFirstRunWelcomeTick(
        status({ state: "installing" }),
        false,
        true,
        "downloading",
      ),
    ).toEqual({ action: "login" })
  })

  it("welcome tick: trust missing → failed with message", () => {
    const tick = evaluateFirstRunWelcomeTick(
      status({ state: "not_configured" }),
      false,
      false,
      "downloading",
    )
    expect(tick.action).toBe("failed")
    expect(tick.failureMessage).toContain("not configured")
  })

  it("welcome tick: error state → failed", () => {
    const tick = evaluateFirstRunWelcomeTick(
      status({ state: "error" }),
      false,
      false,
      "downloading",
    )
    expect(tick.action).toBe("failed")
  })
})