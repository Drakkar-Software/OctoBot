export const LOGIN_SESSION_CLEARED_STORAGE_KEY = "octobot_login_session_cleared"

export function markLoginSessionCleared(): void {
  sessionStorage.setItem(LOGIN_SESSION_CLEARED_STORAGE_KEY, "1")
}

export function consumeLoginSessionClearedHint(): boolean {
  const value = sessionStorage.getItem(LOGIN_SESSION_CLEARED_STORAGE_KEY)
  if (!value) {
    return false
  }
  sessionStorage.removeItem(LOGIN_SESSION_CLEARED_STORAGE_KEY)
  return true
}
