/**
 * Share OctoBot logs into the user's OctoChat support ticket.
 *
 * The "Share logs" toolbar action fetches the selected OctoBots' log files from the node
 * (`POST /api/v1/logs/export`, returning a zip) and attaches them to the EXISTING support ticket
 * via the OctoChat SDK — the same "fetch bytes from the web server → push through the SDK" pattern
 * used by the debug-state share. It never creates a ticket (creation lives only in Settings): when
 * there is no open ticket it reports the ticket state so the UI can guide the user to Settings.
 */

import { loadPassword } from "@/lib/device-key"
import { getSupportTicket, sendAttachment } from "@/lib/octochat"

export type ShareLogsOutcome =
  | { status: "shared"; nodeId: string }
  | { status: "none" }
  | { status: "pending" }
  | { status: "disabled" }

async function buildAuthHeader(): Promise<string> {
  const username = localStorage.getItem("auth_username") || "node"
  const password = (await loadPassword()) ?? ""
  return `Basic ${btoa(`${username}:${password}`)}`
}

/** Timestamped name for the shared logs archive (mirrors the debug-export filename style). */
export function buildLogsExportFilename(): string {
  const stamp = new Date()
    .toISOString()
    .replace(/[-:]/g, "")
    .replace(/\..+/, "")
    .slice(0, 13)
  return `workflow-logs-${stamp}.zip`
}

/** Fetch the selected OctoBots' logs from the node as a zip file ready to attach. */
export async function fetchWorkflowLogs(
  taskIds: string[],
): Promise<{ bytes: Uint8Array; name: string; mime: string }> {
  const res = await fetch("/api/v1/logs/export", {
    method: "POST",
    headers: {
      Authorization: await buildAuthHeader(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ task_ids: taskIds }),
  })
  if (res.status === 404) {
    throw new Error("No logs found for the selected OctoBots")
  }
  if (!res.ok) {
    throw new Error(`Failed to fetch logs (${res.status})`)
  }
  const buf = await res.arrayBuffer()
  return {
    bytes: new Uint8Array(buf),
    name: buildLogsExportFilename(),
    mime: "application/zip",
  }
}

/**
 * Attach the selected OctoBots' logs to the current support ticket.
 *
 * Only an "open" ticket can receive the logs (E2EE writes require an accepted ticket). For any
 * other state the matching ticket status is returned unchanged so the caller can prompt the user.
 */
export async function shareWorkflowLogs(
  taskIds: string[],
): Promise<ShareLogsOutcome> {
  const ticket = await getSupportTicket()
  if (ticket.status === "open") {
    const file = await fetchWorkflowLogs(taskIds)
    await sendAttachment(ticket.nodeId, file, "Workflow logs")
    return { status: "shared", nodeId: ticket.nodeId }
  }
  if (ticket.status === "resolved") return { status: "none" }
  return ticket
}
