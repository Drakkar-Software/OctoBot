import type { MobileUiStatusResponse } from "@/client"

import {
  mobileUiErrorMessage,
  MOBILE_UI_HEADER_LABEL_GET,
  MOBILE_UI_HEADER_LABEL_INSTALLING,
  MOBILE_UI_STATUS_POLL_MS,
} from "@/lib/mobile-ui"

export const FIRST_RUN_MOBILE_UI_QUERY_KEY = [
  "mobile-ui",
  "first-run",
  "status",
] as const

export const FIRST_RUN_MOBILE_UI_POLL_MS = MOBILE_UI_STATUS_POLL_MS

export const FIRST_RUN_WELCOME_TITLE = "OctoBot browser app"
export const FIRST_RUN_WELCOME_RECOMMENDED_LABEL = "Recommended"
export const FIRST_RUN_WELCOME_DESCRIPTION =
  "The most intuitive way for most people to use OctoBot, and the best place to start."
export const FIRST_RUN_WELCOME_OPEN_LABEL = "Open browser app"
export const FIRST_RUN_WELCOME_DOWNLOAD_LABEL = MOBILE_UI_HEADER_LABEL_GET
export const FIRST_RUN_WELCOME_DOWNLOADING_LABEL = MOBILE_UI_HEADER_LABEL_INSTALLING
export const FIRST_RUN_CONFIGURED_LOGIN_HINT =
  "This node already has a wallet. Sign in to continue, including while the OctoBot browser app finishes downloading."

export type FirstRunWelcomePhase =
  | "choose"
  | "downloading"
  | "configured_login"
  | "failed"

export type FirstRunMobileUiPollOptions = {
  downloadInProgress: boolean
}

export function shouldPollFirstRunMobileUi(
  status: MobileUiStatusResponse | undefined,
  options: FirstRunMobileUiPollOptions,
): boolean {
  if (options.downloadInProgress) {
    return true
  }
  return status?.state === "installing"
}

export type FirstRunWelcomeMobileAction = "busy" | "retry" | "open" | "download"

export function shouldResumeFirstRunDownload(
  phase: FirstRunWelcomePhase,
  status: MobileUiStatusResponse | undefined,
): boolean {
  return phase === "choose" && status?.state === "installing"
}

export function resolveFirstRunWelcomeMobileAction(
  phase: FirstRunWelcomePhase,
  mobileStatus: MobileUiStatusResponse | undefined,
  nodeConfigured: boolean,
): FirstRunWelcomeMobileAction {
  if (phase === "downloading" || shouldResumeFirstRunDownload(phase, mobileStatus)) {
    return "busy"
  }
  if (phase === "failed") {
    return "retry"
  }
  if (
    phase === "choose" &&
    mobileStatus?.state === "ready" &&
    !nodeConfigured &&
    !isFirstRunFailureState(mobileStatus)
  ) {
    return "open"
  }
  return "download"
}

export function isFirstRunFailureState(
  status: MobileUiStatusResponse | undefined,
): boolean {
  if (!status) {
    return false
  }
  if (status.state === "not_configured" || status.state === "error") {
    return true
  }
  return status.last_error != null && status.state !== "installing"
}

export function getFirstRunFailureMessage(
  status: MobileUiStatusResponse | undefined,
): string | null {
  if (!status) {
    return null
  }
  return (
    mobileUiErrorMessage(status.last_error) ??
    (status.state === "not_configured"
      ? "OctoBot browser app download is not configured on this node yet."
      : null)
  )
}

export function canOpenFirstRunMobileOnboarding(
  mobileStatus: MobileUiStatusResponse | undefined,
  nodeConfigured: boolean,
): boolean {
  return (
    mobileStatus?.state === "ready" &&
    !nodeConfigured &&
    !isFirstRunFailureState(mobileStatus)
  )
}

export type FirstRunWelcomeTickAction =
  | "continue"
  | "login"
  | "failed"
  | "open_mobile"

export function canApplyFirstRunOpenMobile(welcomePhase: FirstRunWelcomePhase): boolean {
  return welcomePhase === "downloading"
}

export function evaluateFirstRunWelcomeTick(
  mobileStatus: MobileUiStatusResponse | undefined,
  nodeConfigured: boolean | undefined,
  firstRunConflict: boolean,
  welcomePhase: FirstRunWelcomePhase = "downloading",
): { action: FirstRunWelcomeTickAction; failureMessage?: string | null } {
  if (firstRunConflict || nodeConfigured === true) {
    return { action: "login" }
  }
  if (isFirstRunFailureState(mobileStatus)) {
    return {
      action: "failed",
      failureMessage: getFirstRunFailureMessage(mobileStatus),
    }
  }
  if (
    canOpenFirstRunMobileOnboarding(mobileStatus, nodeConfigured ?? false) &&
    canApplyFirstRunOpenMobile(welcomePhase)
  ) {
    return { action: "open_mobile" }
  }
  return { action: "continue" }
}