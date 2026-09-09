import type { AxiosResponse } from "axios"

import { isAuthLoginRedirectSuppressed } from "@/lib/auth-login-redirect-suppression"

export function shouldSkipLoginRedirectOn401(): boolean {
  return isAuthLoginRedirectSuppressed()
}

export function shouldRedirectToLoginOn401(
  response: AxiosResponse,
  options: {
    pathname: string
    isRedirectingOnAuthFailure: boolean
  },
): boolean {
  if (response.status !== 401) {
    return false
  }
  if (options.isRedirectingOnAuthFailure) {
    return false
  }
  if (options.pathname.endsWith("/login")) {
    return false
  }
  if (shouldSkipLoginRedirectOn401()) {
    return false
  }
  return true
}
