import "./index.css"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { bootstrapApp } from "@/bootstrap-app"
import { RecoveryScreen } from "@/components/Common/RecoveryScreen"
import { reportBootFailed } from "@/lib/shell-error-reporting"
import { createRoot } from "react-dom/client"
import { StrictMode } from "react"

const bootFailedQueryClient = new QueryClient()

void bootstrapApp().catch((error: unknown) => {
  const rootElement = document.getElementById("root")
  const bootError =
    error instanceof Error ? error : new Error(String(error))
  reportBootFailed(bootError)
  if (rootElement) {
    createRoot(rootElement).render(
      <StrictMode>
        <QueryClientProvider client={bootFailedQueryClient}>
          <RecoveryScreen failureKind="boot_failed" />
        </QueryClientProvider>
      </StrictMode>,
    )
  }
})
