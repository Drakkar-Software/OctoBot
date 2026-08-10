import type { ChildOctoBotProcessState } from "@/client"

export function buildProcessBotUrl(webPort: number): string {
  return `http://${window.location.hostname}:${webPort}`
}

export function formatProcessAddress(
  childProcess: ChildOctoBotProcessState,
): string {
  const processBotUrl = buildProcessBotUrl(childProcess.web_port)
  const parsedUrl = new URL(processBotUrl)
  const host = parsedUrl.hostname
  const port =
    parsedUrl.port || (parsedUrl.protocol === "https:" ? "443" : "80")
  return `${host}:${port}`
}
