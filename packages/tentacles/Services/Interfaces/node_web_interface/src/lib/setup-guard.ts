/**
 * Pure helper for setup route guards.
 *
 * Returns the path to redirect to, or null to allow the current setup route.
 *
 * Rules:
 * - Unconfigured node (no wallet yet): always null — show creation form for all setup steps.
 * - Configured node on the wallet-creation step (/setup exactly): redirect away — the form
 *   must never be reachable once a wallet exists, regardless of setup_in_progress.
 * - Configured node on post-creation steps (first-bot, mobile-app): allow only during an
 *   active setup_in_progress session; otherwise redirect to / or /login.
 */
export function getSetupRedirect(opts: {
  configured: boolean
  setupInProgress: boolean
  loggedIn: boolean
  pathname: string
}): string | null {
  const { configured, setupInProgress, loggedIn, pathname } = opts
  if (!configured) return null

  const onCreationStep = pathname.replace(/\/+$/, "").endsWith("/setup")
  if (onCreationStep) {
    if (loggedIn) return setupInProgress ? "/setup/first-bot" : "/"
    return "/login"
  }

  return setupInProgress ? null : loggedIn ? "/" : "/login"
}
