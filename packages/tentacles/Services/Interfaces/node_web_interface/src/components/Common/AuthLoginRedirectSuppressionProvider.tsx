import { useEffect } from "react"

import {
  acquireAuthLoginRedirectSuppression,
  releaseAuthLoginRedirectSuppression,
} from "@/lib/auth-login-redirect-suppression"

type AuthLoginRedirectSuppressionProviderProps = {
  children: React.ReactNode
}

export function AuthLoginRedirectSuppressionProvider({
  children,
}: AuthLoginRedirectSuppressionProviderProps) {
  useEffect(() => {
    acquireAuthLoginRedirectSuppression()
    return () => releaseAuthLoginRedirectSuppression()
  }, [])

  return children
}
