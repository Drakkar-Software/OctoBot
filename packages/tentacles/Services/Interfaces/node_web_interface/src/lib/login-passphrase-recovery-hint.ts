export const LOGIN_PASSPHRASE_RECOVERY_SUCCESS_STORAGE_KEY =
  "octobot_login_passphrase_recovery_success"

export function markLoginPassphraseRecoverySuccess(): void {
  sessionStorage.setItem(LOGIN_PASSPHRASE_RECOVERY_SUCCESS_STORAGE_KEY, "1")
}

export function consumeLoginPassphraseRecoverySuccessHint(): boolean {
  const value = sessionStorage.getItem(LOGIN_PASSPHRASE_RECOVERY_SUCCESS_STORAGE_KEY)
  if (!value) {
    return false
  }
  sessionStorage.removeItem(LOGIN_PASSPHRASE_RECOVERY_SUCCESS_STORAGE_KEY)
  return true
}
