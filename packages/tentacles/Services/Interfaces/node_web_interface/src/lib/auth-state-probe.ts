import { loadPassword } from "@/lib/device-key"

export type AuthStateProbeResult = "ok" | "broken" | "skipped"

export async function probeAuthState(): Promise<AuthStateProbeResult> {
  if (sessionStorage.getItem("setup_in_progress")) {
    return "skipped"
  }
  const username = localStorage.getItem("auth_username")
  if (!username) {
    return "ok"
  }
  try {
    const password = await loadPassword()
    if (password === null) {
      return "broken"
    }
    return "ok"
  } catch {
    return "broken"
  }
}
