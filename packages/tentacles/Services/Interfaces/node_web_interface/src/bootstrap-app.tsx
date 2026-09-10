import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { createRouter, RouterProvider } from "@tanstack/react-router"
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { ErrorBoundary } from "react-error-boundary"
import { OpenAPI } from "@/client"
import InsecureContextNotice from "@/components/Common/InsecureContextNotice"
import { RecoveryScreen } from "@/components/Common/RecoveryScreen"
import { ThemeProvider } from "@/components/theme-provider"
import { Toaster } from "@/components/ui/sonner"
import { clearAuth } from "@/hooks/useAuth"
import { probeAuthState } from "@/lib/auth-state-probe"
import { markBootSucceeded } from "@/lib/boot-watchdog"
import { loadPassword } from "@/lib/device-key"
import type { RecoveryFailureKind } from "@/components/Common/RecoveryScreen"
import { isWebCryptoAvailable } from "@/lib/secure-context"
import {
  reportAuthStateBroken,
  reportShellFatalError,
} from "@/lib/shell-error-reporting"
import { routeTree } from "@/routeTree.gen"

export function configureOpenApi(): void {
  OpenAPI.BASE =
    import.meta.env.NODE_API_URL ||
    (import.meta.env.DEV ? "http://localhost:8000" : "")
  OpenAPI.USERNAME = async () => {
    return localStorage.getItem("auth_username") || ""
  }
  OpenAPI.PASSWORD = async () => {
    return (await loadPassword()) ?? ""
  }

  let isRedirectingOnAuthFailure = false
  OpenAPI.interceptors.response.use((response) => {
    if (response.status === 401 && !isRedirectingOnAuthFailure) {
      const onLoginPage = window.location.pathname.endsWith("/login")
      if (!onLoginPage) {
        isRedirectingOnAuthFailure = true
        void clearAuth().finally(() => {
          window.location.href = "/app/login"
        })
      }
    }
    return response
  })
}

function createAppRouter() {
  return createRouter({
    routeTree,
    basepath: "/app",
  })
}

type RecoveryView =
  | { mode: "recovery"; failureKind: RecoveryFailureKind }
  | { mode: "app" }

async function resolveStartupView(): Promise<RecoveryView> {
  const authState = await probeAuthState()
  if (authState === "broken") {
    reportAuthStateBroken()
    return { mode: "recovery", failureKind: "auth_broken" }
  }
  return { mode: "app" }
}

function renderRecovery(
  rootElement: HTMLElement,
  failureKind: RecoveryFailureKind,
): void {
  createRoot(rootElement).render(
    <StrictMode>
      <RecoveryScreen failureKind={failureKind} />
    </StrictMode>,
  )
  markBootSucceeded()
}

export function ShellErrorFallback() {
  return <RecoveryScreen failureKind="fatal_render" />
}

export function handleShellRenderError(error: unknown): void {
  reportShellFatalError(
    error instanceof Error ? error : new Error(String(error)),
  )
}

function renderApp(rootElement: HTMLElement): void {
  const queryClient = new QueryClient()
  const router = createAppRouter()

  createRoot(rootElement).render(
    <StrictMode>
      <ErrorBoundary
        FallbackComponent={ShellErrorFallback}
        onError={handleShellRenderError}
      >
        <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
          {isWebCryptoAvailable() ? (
            <QueryClientProvider client={queryClient}>
              <RouterProvider router={router} />
              <Toaster richColors closeButton />
            </QueryClientProvider>
          ) : (
            <InsecureContextNotice />
          )}
        </ThemeProvider>
      </ErrorBoundary>
    </StrictMode>,
  )
  markBootSucceeded()
}

export async function bootstrapApp(): Promise<void> {
  configureOpenApi()
  const rootElement = document.getElementById("root")
  if (!rootElement) {
    throw new Error("Root element not found")
  }

  const startupView = await resolveStartupView()
  if (startupView.mode === "recovery") {
    renderRecovery(rootElement, startupView.failureKind)
    return
  }
  renderApp(rootElement)
}
