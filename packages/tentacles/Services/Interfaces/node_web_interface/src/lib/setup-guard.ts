/**
 * Pure helper for setup route guards.
 *
 * Returns the path to redirect to, or null to allow the current setup route.
 *
 * Rules:
 * - Unconfigured node (no wallet yet): always null — show creation form for all setup steps.
 * - Configured node on the wallet-creation step (/setup or /setup/welcome): redirect away — the form
 *   must never be reachable once a wallet exists, regardless of setup_in_progress.
 * - Configured node on post-creation steps (first-bot, mobile-app): allow only during an
 *   active setup_in_progress session; otherwise redirect to / or /login.
 */
export function isPreWalletSetupRoute(pathname: string): boolean {
  const normalized = pathname.replace(/\/+$/, "") || "/"
  return normalized === "/setup" || normalized.endsWith("/setup/welcome")
}

export const START_FRESH_FROM_RECOVER_KEY = "start_fresh_from_recover"

export function getSetupRedirect(opts: {
  configured: boolean
  setupInProgress: boolean
  loggedIn: boolean
  pathname: string
  startFreshFromRecover?: boolean
}): string | null {
  const { configured, setupInProgress, loggedIn, pathname, startFreshFromRecover } =
    opts
  if (!configured) return null

  if (startFreshFromRecover && isPreWalletSetupRoute(pathname)) {
    return null
  }

  if (isPreWalletSetupRoute(pathname)) {
    if (loggedIn) return setupInProgress ? "/setup/connect" : "/"
    return "/login"
  }

  return setupInProgress ? null : loggedIn ? "/" : "/login"
}
