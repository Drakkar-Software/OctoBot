export const LOGIN_PASSPHRASE_RECOVERED_STORAGE_KEY =
  "octobot_login_passphrase_recovered"

export function markLoginPassphraseRecovered(): void {
  sessionStorage.setItem(LOGIN_PASSPHRASE_RECOVERED_STORAGE_KEY, "1")
}

export function consumeLoginPassphraseRecoveredHint(): boolean {
  const value = sessionStorage.getItem(LOGIN_PASSPHRASE_RECOVERED_STORAGE_KEY)
  if (!value) {
    return false
  }
  sessionStorage.removeItem(LOGIN_PASSPHRASE_RECOVERED_STORAGE_KEY)
  return true
}
