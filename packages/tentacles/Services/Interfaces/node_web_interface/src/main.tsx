import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { createRouter, RouterProvider } from "@tanstack/react-router"
import { StrictMode } from "react"
import ReactDOM from "react-dom/client"
import { OpenAPI } from "./client"
import { ThemeProvider } from "./components/theme-provider"
import { Toaster } from "./components/ui/sonner"
import "./index.css"
import { clearAuth } from "./hooks/useAuth"
import { loadPassword } from "./lib/device-key"
import { routeTree } from "./routeTree.gen"

OpenAPI.BASE =
  import.meta.env.NODE_API_URL ||
  (import.meta.env.DEV ? "http://localhost:8000" : "")
OpenAPI.USERNAME = async () => {
  return localStorage.getItem("auth_username") || ""
}
OpenAPI.PASSWORD = async () => {
  return (await loadPassword()) ?? ""
}

// Response interceptor: when the backend returns 401 on any authenticated request
// (e.g. polled /tasks/), tear down local credentials and bounce the user to /login.
// Running at the request layer (before React Query sees the error) stops refetch
// loops immediately — react-query never gets a chance to retry-on-interval with
// stale Basic auth credentials. The /login route itself is excluded so a failed
// login attempt does not redirect to itself.
//
// Setup endpoints (/setup/init, /setup/status) are unauthenticated and never return
// 401, so they pass through this interceptor untouched.
let isRedirectingOnAuthFailure = false
OpenAPI.interceptors.response.use((response) => {
  if (response.status === 401 && !isRedirectingOnAuthFailure) {
    const onLoginPage = window.location.pathname.endsWith("/login")
    if (!onLoginPage) {
      isRedirectingOnAuthFailure = true
      // Fire-and-forget clear, then hard navigate. We don't await — the redirect
      // below tears down the SPA anyway and the page will reload fresh.
      void clearAuth().finally(() => {
        window.location.href = "/app/login"
      })
    }
  }
  return response
})

const queryClient = new QueryClient()

const router = createRouter({
  routeTree,
  basepath: "/app",
})
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        <Toaster richColors closeButton />
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
)
