let authLoginRedirectSuppressionCount = 0

export function acquireAuthLoginRedirectSuppression(): void {
  authLoginRedirectSuppressionCount += 1
}

export function releaseAuthLoginRedirectSuppression(): void {
  authLoginRedirectSuppressionCount = Math.max(
    0,
    authLoginRedirectSuppressionCount - 1,
  )
}

export function isAuthLoginRedirectSuppressed(): boolean {
  return authLoginRedirectSuppressionCount > 0
}

/** Reset for unit tests only. */
export function resetAuthLoginRedirectSuppressionForTests(): void {
  authLoginRedirectSuppressionCount = 0
}
