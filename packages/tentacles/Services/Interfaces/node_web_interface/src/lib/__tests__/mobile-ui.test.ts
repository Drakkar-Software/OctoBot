import { describe, expect, it } from "vitest"

import type { MobileUiErrorCode, MobileUiStatusResponse } from "@/client"
import {
  buildMobileUiBotUrl,
  buildMobileUiBotsNewUrl,
  buildMobileUiUrl,
  getMobileUiHeaderAction,
  getMobileUiView,
  isMobileUiUpToDate,
  MOBILE_UI_DESCRIPTION,
  MOBILE_UI_HEADER_LABEL_GET,
  MOBILE_UI_HEADER_LABEL_INSTALLED,
  MOBILE_UI_HEADER_LABEL_INSTALLING,
  MOBILE_UI_TITLE,
  mobileUiErrorMessage,
  shouldPollMobileUi,
} from "@/lib/mobile-ui"

const baseStatus = (
  overrides: Partial<MobileUiStatusResponse> &
    Pick<MobileUiStatusResponse, "state">,
): MobileUiStatusResponse => ({
  installed_version: null,
  latest_version: null,
  update_available: false,
  last_error: null,
  ...overrides,
})

describe("buildMobileUiUrl", () => {
  it("uses origin when apiBase is empty", () => {
    expect(buildMobileUiUrl("", "http://192.168.0.10:5001")).toBe(
      "http://192.168.0.10:5001/mobile/",
    )
  })

  it("uses apiBase when set", () => {
    expect(
      buildMobileUiUrl("http://localhost:8000", "http://localhost:5173"),
    ).toBe("http://localhost:8000/mobile/")
  })
})

describe("buildMobileUiBotsNewUrl", () => {
  it("uses origin when apiBase is empty", () => {
    expect(buildMobileUiBotsNewUrl("", "http://192.168.0.10:5001")).toBe(
      "http://192.168.0.10:5001/mobile/bots/new",
    )
  })

  it("uses apiBase when set", () => {
    expect(
      buildMobileUiBotsNewUrl("http://localhost:8000", "http://localhost:5173"),
    ).toBe("http://localhost:8000/mobile/bots/new")
  })
})

describe("mobileUiErrorMessage", () => {
  const codes: MobileUiErrorCode[] = [
    "not_configured",
    "manifest_fetch_failed",
    "manifest_invalid",
    "signature_invalid",
    "download_failed",
    "integrity_check_failed",
    "install_failed",
    "rollback_rejected",
  ]

  it("returns null for not_configured and null", () => {
    expect(mobileUiErrorMessage("not_configured")).toBeNull()
    expect(mobileUiErrorMessage(null)).toBeNull()
  })

  it.each(codes.filter((c) => c !== "not_configured"))(
    "returns plain language for %s without em dash",
    (code) => {
      const message = mobileUiErrorMessage(code)
      expect(message).toBeTruthy()
      expect(message).not.toContain("—")
    },
  )

  it("maps manifest_fetch_failed", () => {
    expect(mobileUiErrorMessage("manifest_fetch_failed")).toBe(
      "Could not reach the update server. Check your internet connection and try again.",
    )
  })

  it("maps verification failures", () => {
    const expected =
      "The download could not be verified, so it was not installed. Try again later."
    expect(mobileUiErrorMessage("manifest_invalid")).toBe(expected)
    expect(mobileUiErrorMessage("signature_invalid")).toBe(expected)
    expect(mobileUiErrorMessage("integrity_check_failed")).toBe(expected)
  })

  it("maps download_failed and install_failed", () => {
    expect(mobileUiErrorMessage("download_failed")).toBe(
      "The download did not finish. Try again.",
    )
    expect(mobileUiErrorMessage("install_failed")).toBe(
      "Could not save the interface on this computer. Try again.",
    )
  })

  it("maps rollback_rejected", () => {
    expect(mobileUiErrorMessage("rollback_rejected")).toBe(
      "The update server offered an older version than the one installed, so it was ignored.",
    )
  })
})

describe("getMobileUiView", () => {
  it("returns hidden for undefined status", () => {
    expect(getMobileUiView(undefined, true)).toEqual({ kind: "hidden" })
    expect(getMobileUiView(undefined, false)).toEqual({ kind: "hidden" })
  })

  it("returns hidden for not_configured", () => {
    const status = baseStatus({ state: "not_configured" })
    expect(getMobileUiView(status, true)).toEqual({ kind: "hidden" })
    expect(getMobileUiView(status, false)).toEqual({ kind: "hidden" })
  })

  it("returns install for admin not_installed and hidden for non-admin", () => {
    const status = baseStatus({ state: "not_installed" })
    expect(getMobileUiView(status, true)).toEqual({
      kind: "install",
      error: null,
    })
    expect(getMobileUiView(status, false)).toEqual({ kind: "hidden" })
  })

  it("returns install with error for admin error state", () => {
    const status = baseStatus({
      state: "error",
      last_error: "download_failed",
    })
    expect(getMobileUiView(status, true)).toEqual({
      kind: "install",
      error: "The download did not finish. Try again.",
    })
    expect(getMobileUiView(status, false)).toEqual({ kind: "hidden" })
  })

  it("returns installing for admin and non-admin", () => {
    const status = baseStatus({ state: "installing" })
    expect(getMobileUiView(status, true)).toEqual({ kind: "installing" })
    expect(getMobileUiView(status, false)).toEqual({ kind: "installing" })
  })

  it("returns ready with admin update controls", () => {
    const status = baseStatus({
      state: "ready",
      installed_version: "1.0.0",
      latest_version: "2.0.0",
      update_available: true,
    })
    expect(getMobileUiView(status, true)).toEqual({
      kind: "ready",
      version: "1.0.0",
      latestVersion: "2.0.0",
      canCheckForUpdates: true,
      updateAvailable: true,
      error: null,
    })
  })

  it("sets latestVersion to null when update is not available", () => {
    const status = baseStatus({
      state: "ready",
      installed_version: "1.0.0",
      latest_version: "2.0.0",
      update_available: false,
    })
    expect(getMobileUiView(status, true)).toEqual({
      kind: "ready",
      version: "1.0.0",
      latestVersion: null,
      canCheckForUpdates: true,
      updateAvailable: false,
      error: null,
    })
  })

  it("returns ready without update controls for non-admin", () => {
    const status = baseStatus({
      state: "ready",
      installed_version: "1.0.0",
      update_available: true,
    })
    expect(getMobileUiView(status, false)).toEqual({
      kind: "ready",
      version: "1.0.0",
      latestVersion: null,
      canCheckForUpdates: false,
      updateAvailable: true,
      error: null,
    })
  })

  it("returns ready with last_error for admin and hides error for non-admin", () => {
    const status = baseStatus({
      state: "ready",
      installed_version: "1.0.0",
      last_error: "download_failed",
    })
    expect(getMobileUiView(status, true)).toEqual({
      kind: "ready",
      version: "1.0.0",
      latestVersion: null,
      canCheckForUpdates: true,
      updateAvailable: false,
      error: "The download did not finish. Try again.",
    })
    expect(getMobileUiView(status, false)).toEqual({
      kind: "ready",
      version: "1.0.0",
      latestVersion: null,
      canCheckForUpdates: false,
      updateAvailable: false,
      error: null,
    })
  })
})

describe("shouldPollMobileUi", () => {
  it("polls only while installing", () => {
    expect(shouldPollMobileUi(undefined)).toBe(false)
    expect(shouldPollMobileUi(baseStatus({ state: "ready" }))).toBe(false)
    expect(shouldPollMobileUi(baseStatus({ state: "installing" }))).toBe(true)
  })
})

describe("getMobileUiHeaderAction", () => {
  it("returns hidden for undefined status and not_configured", () => {
    expect(getMobileUiHeaderAction(getMobileUiView(undefined, true))).toEqual({
      kind: "hidden",
    })
    expect(getMobileUiHeaderAction(getMobileUiView(undefined, false))).toEqual({
      kind: "hidden",
    })
    const notConfigured = baseStatus({ state: "not_configured" })
    expect(getMobileUiHeaderAction(getMobileUiView(notConfigured, true))).toEqual({
      kind: "hidden",
    })
  })

  it("returns get for admin not_installed and hidden for non-admin", () => {
    const status = baseStatus({ state: "not_installed" })
    expect(getMobileUiHeaderAction(getMobileUiView(status, true))).toEqual({
      kind: "get",
    })
    expect(getMobileUiHeaderAction(getMobileUiView(status, false))).toEqual({
      kind: "hidden",
    })
  })

  it("returns get for admin error state", () => {
    const status = baseStatus({
      state: "error",
      last_error: "download_failed",
    })
    expect(getMobileUiHeaderAction(getMobileUiView(status, true))).toEqual({
      kind: "get",
    })
  })

  it("returns installing for admin and non-admin", () => {
    const status = baseStatus({ state: "installing" })
    expect(getMobileUiHeaderAction(getMobileUiView(status, true))).toEqual({
      kind: "installing",
    })
    expect(getMobileUiHeaderAction(getMobileUiView(status, false))).toEqual({
      kind: "installing",
    })
  })

  it("returns open for admin ready with update_available", () => {
    const status = baseStatus({
      state: "ready",
      installed_version: "1.0.0",
      latest_version: "2.0.0",
      update_available: true,
    })
    expect(getMobileUiHeaderAction(getMobileUiView(status, true))).toEqual({
      kind: "open",
    })
  })

  it("returns open for admin ready without update", () => {
    const status = baseStatus({
      state: "ready",
      installed_version: "1.0.0",
      update_available: false,
    })
    expect(getMobileUiHeaderAction(getMobileUiView(status, true))).toEqual({
      kind: "open",
    })
  })

  it("returns open for non-admin ready with update_available", () => {
    const status = baseStatus({
      state: "ready",
      installed_version: "1.0.0",
      update_available: true,
    })
    expect(getMobileUiHeaderAction(getMobileUiView(status, false))).toEqual({
      kind: "open",
    })
  })
})

describe("isMobileUiUpToDate", () => {
  it("is true only for ready view after successful check with no update or error", () => {
    const ready = getMobileUiView(
      baseStatus({
        state: "ready",
        installed_version: "1.0.0",
        update_available: false,
      }),
      true,
    )
    expect(isMobileUiUpToDate(ready, true)).toBe(true)
    expect(isMobileUiUpToDate(ready, false)).toBe(false)
    const withUpdate = getMobileUiView(
      baseStatus({
        state: "ready",
        installed_version: "1.0.0",
        update_available: true,
      }),
      true,
    )
    expect(isMobileUiUpToDate(withUpdate, true)).toBe(false)
  })
})

describe("mobile ui copy constants", () => {
  it("uses no em dash in title, description, and header labels", () => {
    for (const value of [
      MOBILE_UI_TITLE,
      MOBILE_UI_DESCRIPTION,
      MOBILE_UI_HEADER_LABEL_INSTALLED,
      MOBILE_UI_HEADER_LABEL_GET,
      MOBILE_UI_HEADER_LABEL_INSTALLING,
    ]) {
      expect(value).not.toContain("—")
    }
  })
})
