import { client } from "@/client/client.gen"
import { buildBasicAuthorizationHeader } from "@/lib/basic-auth"
import { loadPassword } from "@/lib/device-key"
import { markLoginSessionCleared } from "@/lib/login-session-hint"
import { shouldRedirectToLoginOn401 } from "@/lib/open-api-401-login-redirect"
import { clearAuth } from "@/hooks/useAuth"
import { resolveApiBaseUrl } from "@/lib/hey-api-client-config"

let isApiClientConfigured = false
let isRedirectingOnAuthFailure = false

export function getApiBaseUrl(): string {
  return resolveApiBaseUrl()
}

export function resetApiClientConfigurationForTests(): void {
  isApiClientConfigured = false
  isRedirectingOnAuthFailure = false
}

export function configureApiClient(): void {
  if (isApiClientConfigured) {
    return
  }
  isApiClientConfigured = true

  client.setConfig({
    baseURL: getApiBaseUrl(),
    throwOnError: true,
  })

  client.instance.interceptors.request.use(async (config) => {
    const username = localStorage.getItem("auth_username") ?? ""
    const password = (await loadPassword()) ?? ""
    if (username && password) {
      config.headers.set(
        "Authorization",
        buildBasicAuthorizationHeader(username, password),
      )
    }
    return config
  })

  client.instance.interceptors.response.use((response) => {
    if (
      shouldRedirectToLoginOn401(response, {
        pathname: window.location.pathname,
        isRedirectingOnAuthFailure,
      })
    ) {
      isRedirectingOnAuthFailure = true
      markLoginSessionCleared()
      void clearAuth().finally(() => {
        window.location.href = "/app/login"
      })
    }
    return response
  })
}
