import type {
  MobileUiErrorCode,
  MobileUiStatusResponse,
} from "@/client"

export const MOBILE_UI_PATH = "/mobile/"
export const MOBILE_UI_STATUS_POLL_MS = 1500
export const MOBILE_UI_STATUS_QUERY_KEY = ["mobile-ui", "status"] as const

export const MOBILE_UI_TITLE = "OctoBot browser app on this node"
export const MOBILE_UI_DESCRIPTION =
  "Use OctoBot in your browser, straight from this node. The first time, the node downloads it from OctoBot."
export const MOBILE_UI_HEADER_LABEL_INSTALLED = "OctoBot browser app"
export const MOBILE_UI_HEADER_LABEL_GET = "Get the browser app"
export const MOBILE_UI_HEADER_LABEL_INSTALLING = "Downloading..."

export type MobileUiHeaderAction =
  | { kind: "hidden" }
  | { kind: "get" }
  | { kind: "installing" }
  | { kind: "open" }

export type MobileUiView =
  | { kind: "hidden" }
  | { kind: "install"; error: string | null }
  | { kind: "installing" }
  | {
      kind: "ready"
      version: string | null
      latestVersion: string | null
      canCheckForUpdates: boolean
      updateAvailable: boolean
      error: string | null
    }

export function buildMobileUiUrl(
  apiBase: string | undefined,
  origin: string,
): string {
  if (apiBase) {
    return new URL(MOBILE_UI_PATH, apiBase).toString()
  }
  return new URL(MOBILE_UI_PATH, origin).toString()
}

export function mobileUiErrorMessage(
  code: MobileUiErrorCode | null,
): string | null {
  switch (code) {
    case "manifest_fetch_failed":
      return "Could not reach the update server. Check your internet connection and try again."
    case "manifest_invalid":
    case "signature_invalid":
    case "integrity_check_failed":
      return "The download could not be verified, so it was not installed. Try again later."
    case "download_failed":
      return "The download did not finish. Try again."
    case "install_failed":
      return "Could not save the interface on this computer. Try again."
    case "rollback_rejected":
      return "The update server offered an older version than the one installed, so it was ignored."
    case "not_configured":
    case null:
      return null
    default: {
      const _exhaustive: never = code
      return _exhaustive
    }
  }
}

export function getMobileUiHeaderAction(view: MobileUiView): MobileUiHeaderAction {
  switch (view.kind) {
    case "hidden":
      return { kind: "hidden" }
    case "install":
      return { kind: "get" }
    case "installing":
      return { kind: "installing" }
    case "ready":
      return { kind: "open" }
    default: {
      const _exhaustive: never = view
      return _exhaustive
    }
  }
}

export function isMobileUiUpToDate(
  view: MobileUiView,
  checkSucceeded: boolean,
): boolean {
  return (
    view.kind === "ready" &&
    checkSucceeded &&
    !view.updateAvailable &&
    !view.error
  )
}

export function getMobileUiView(
  status: MobileUiStatusResponse | undefined,
  isAdmin: boolean,
): MobileUiView {
  if (!status || status.state === "not_configured") {
    return { kind: "hidden" }
  }
  if (status.state === "installing") {
    return { kind: "installing" }
  }
  if (status.state === "not_installed" || status.state === "error") {
    if (!isAdmin) {
      return { kind: "hidden" }
    }
    return {
      kind: "install",
      error: mobileUiErrorMessage(status.last_error),
    }
  }
  if (status.state === "ready") {
    return {
      kind: "ready",
      version: status.installed_version,
      latestVersion: status.update_available ? status.latest_version : null,
      canCheckForUpdates: isAdmin,
      updateAvailable: status.update_available,
      error: isAdmin ? mobileUiErrorMessage(status.last_error) : null,
    }
  }
  return { kind: "hidden" }
}

export function shouldPollMobileUi(
  status: MobileUiStatusResponse | undefined,
): boolean {
  return status?.state === "installing"
}
