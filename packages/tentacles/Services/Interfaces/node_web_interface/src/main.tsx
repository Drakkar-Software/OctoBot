// Entry point: global styles and async shell bootstrap (router lives in bootstrap-app.tsx).
import "./index.css"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { bootstrapApp } from "@/bootstrap-app"
import { RecoveryScreen } from "@/components/Common/RecoveryScreen"
import { ThemeProvider } from "@/components/theme-provider"
import { Toaster } from "@/components/ui/sonner"
import { reportBootFailed } from "@/lib/shell-error-reporting"

// RecoveryScreen may use React Query (e.g. feedback); separate from the app router client.
const bootFailedQueryClient = new QueryClient()

// Unexpected bootstrapApp() rejections (throws not handled by recovery branches in bootstrap-app).
void bootstrapApp().catch((error: unknown) => {
  const rootElement = document.getElementById("root")
  const bootError =
    error instanceof Error ? error : new Error(String(error))
  // Best-effort ui_boot_failed journal; must not throw.
  reportBootFailed(bootError)
  if (rootElement) {
    // boot_failed: last-resort UI (distinct from auth_broken, insecure_context, fatal_render).
    createRoot(rootElement).render(
      <StrictMode>
        <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
          <QueryClientProvider client={bootFailedQueryClient}>
            <RecoveryScreen failureKind="boot_failed" />
            <Toaster richColors closeButton />
          </QueryClientProvider>
        </ThemeProvider>
      </StrictMode>,
    )
  }
  // If #root is missing, journal still runs but nothing is mounted.
})
