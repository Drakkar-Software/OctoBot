import type { ChildOctoBotProcessState } from "@/client"

export function formatProcessAddress(
  childProcess: ChildOctoBotProcessState,
): string {
  try {
    const parsedUrl = new URL(childProcess.http_base_url)
    const host = parsedUrl.hostname
    const port =
      parsedUrl.port ||
      (parsedUrl.protocol === "https:" ? "443" : "80")
    return `${host}:${port}`
  } catch {
    return `${childProcess.http_base_url}:${childProcess.web_port}`
  }
}
