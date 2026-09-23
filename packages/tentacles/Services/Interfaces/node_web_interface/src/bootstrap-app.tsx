import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { createRouter, RouterProvider } from "@tanstack/react-router"
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { ErrorBoundary } from "react-error-boundary"
import { RecoveryScreen } from "@/components/Common/RecoveryScreen"
import { ThemeProvider } from "@/components/theme-provider"
import { Toaster } from "@/components/ui/sonner"
import { probeAuthState } from "@/lib/auth-state-probe"
import { configureApiClient } from "@/lib/configure-api-client"
import type { RecoveryFailureKind } from "@/components/Common/RecoveryScreen"
import { isWebCryptoAvailable } from "@/lib/secure-context"
import {
  reportAuthStateBroken,
  reportInsecureContext,
  reportShellFatalError,
} from "@/lib/shell-error-reporting"
import { routeTree } from "@/routeTree.gen"

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
  // probeAuthState: skipped during setup; ok when logged out or password present;
  // broken when auth_username exists but IndexedDB password is missing/unreadable.
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
  const queryClient = new QueryClient()

  createRoot(rootElement).render(
    <StrictMode>
      <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
        <QueryClientProvider client={queryClient}>
          <RecoveryScreen failureKind={failureKind} />
          <Toaster richColors closeButton />
        </QueryClientProvider>
      </ThemeProvider>
    </StrictMode>,
  )
}

// Shown when a render error escapes the main app tree (ErrorBoundary fallback).
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
          <QueryClientProvider client={queryClient}>
            <RouterProvider router={router} />
            <Toaster richColors closeButton />
          </QueryClientProvider>
        </ThemeProvider>
      </ErrorBoundary>
    </StrictMode>,
  )
}

// Startup: configure API → mount root → require Web Crypto → auth probe → app or RecoveryScreen.
export async function bootstrapApp(): Promise<void> {
  configureApiClient()
  const rootElement = document.getElementById("root")
  if (!rootElement) {
    throw new Error("Root element not found")
  }

  if (!isWebCryptoAvailable()) {
    // Non-secure context (e.g. HTTP remote UI): crypto.subtle unavailable → insecure_context recovery.
    reportInsecureContext({
      isSecureContext: window.isSecureContext,
      hostname: window.location.hostname,
    })
    renderRecovery(rootElement, "insecure_context")
    return
  }

  const startupView = await resolveStartupView()
  if (startupView.mode === "recovery") {
    renderRecovery(rootElement, startupView.failureKind)
    return
  }
  renderApp(rootElement)
}
