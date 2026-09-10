import "./index.css"
import { bootstrapApp } from "@/bootstrap-app"
import { RecoveryScreen } from "@/components/Common/RecoveryScreen"
import { reportBootFailed } from "@/lib/shell-error-reporting"
import { createRoot } from "react-dom/client"
import { StrictMode } from "react"

void bootstrapApp().catch((error: unknown) => {
  const rootElement = document.getElementById("root")
  const bootError =
    error instanceof Error ? error : new Error(String(error))
  reportBootFailed(bootError)
  if (rootElement) {
    createRoot(rootElement).render(
      <StrictMode>
        <RecoveryScreen failureKind="boot_failed" />
      </StrictMode>,
    )
  }
})
