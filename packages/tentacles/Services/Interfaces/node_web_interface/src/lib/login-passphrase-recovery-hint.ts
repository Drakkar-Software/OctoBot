import { toast } from "sonner"

export const LOGIN_PASSPHRASE_RECOVERY_SUCCESS_STORAGE_KEY =
  "octobot_login_passphrase_recovery_success"

export const LOGIN_PASSPHRASE_RECOVERY_SUCCESS_TOAST_TITLE =
  "Passphrase updated"

export const LOGIN_PASSPHRASE_RECOVERY_SUCCESS_TOAST_DESCRIPTION =
  "Unlock with your new passphrase."

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

export function showLoginPassphraseRecoverySuccessToast(): void {
  toast.success(LOGIN_PASSPHRASE_RECOVERY_SUCCESS_TOAST_TITLE, {
    description: LOGIN_PASSPHRASE_RECOVERY_SUCCESS_TOAST_DESCRIPTION,
  })
}
