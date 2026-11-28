/**
 * Normalize post-login return paths to TanStack router destinations (no `/app` prefix).
 * Keep allowlist in sync with Mobile2 `HANDOFF_APP_PATH` in Astrolab/frontend/mobile2/src/lib/embedded/handoff.ts.
 */
export type SafeReturnToDestination =
  | "/octobots/new"
  | "/settings"
  | "/settings/connect"

export function safeReturnTo(
  raw: string | null | undefined,
): SafeReturnToDestination | null {
  if (raw == null) return null
  let path = raw.trim()
  if (!path) return null
  if (path.includes("://") || path.startsWith("//")) return null
  if (path.includes("?") || path.includes("#")) return null

  while (path.length > 1 && path.endsWith("/")) {
    path = path.slice(0, -1)
  }

  if (path === "/octobots/new" || path === "/app/octobots/new") {
    return "/octobots/new"
  }
  if (path === "/settings/connect" || path === "/app/settings/connect") {
    return "/settings/connect"
  }
  if (path === "/settings" || path === "/app/settings") {
    return "/settings"
  }
  return null
}

export function resolvePostLoginDestination(
  returnTo: string | null | undefined,
): "/" | SafeReturnToDestination {
  return safeReturnTo(returnTo) ?? "/"
}

/** Absolute href for full-page login redirect (401). */
export function loginRedirectHref(browserPathname: string): string {
  const returnTo = safeReturnTo(browserPathname)
  if (!returnTo) return "/app/login"
  return `/app/login?returnTo=${encodeURIComponent(browserPathname)}`
}