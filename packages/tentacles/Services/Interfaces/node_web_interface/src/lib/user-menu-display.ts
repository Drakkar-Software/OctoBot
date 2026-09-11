export const AUTH_IS_SUPERUSER_KEY = "auth_is_superuser"

export function getStoredIsSuperuser(): boolean {
  return localStorage.getItem(AUTH_IS_SUPERUSER_KEY) === "true"
}

export function setStoredIsSuperuser(isSuperuser: boolean): void {
  if (isSuperuser) {
    localStorage.setItem(AUTH_IS_SUPERUSER_KEY, "true")
    return
  }
  localStorage.removeItem(AUTH_IS_SUPERUSER_KEY)
}

export function getCachedNavbarDisplayName(): string {
  const storedWalletName = localStorage.getItem("auth_wallet_name")
  if (storedWalletName) return storedWalletName
  const email = localStorage.getItem("auth_username")
  if (!email) return "—"
  return email.length > 12 ? `${email.slice(0, 6)}…${email.slice(-4)}` : email
}

export function displayName(
  email: string | undefined,
  fullName: string | null | undefined,
): string {
  // Prefer server-sourced name (user.full_name) to avoid showing stale localStorage value
  if (fullName) return fullName
  const stored = localStorage.getItem("auth_wallet_name")
  if (stored) return stored
  if (!email) return "—"
  return email.length > 12 ? `${email.slice(0, 6)}…${email.slice(-4)}` : email
}
