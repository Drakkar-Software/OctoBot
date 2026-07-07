/**
 * Download node or automation log archives (`POST /api/v1/logs/export`).
 */

import { loadPassword } from "@/lib/device-key"

const LOGS_ZIP_MIME = "application/zip"
const NODE_LOGS_NOT_FOUND_MESSAGE = "No logs found in the node logs folder"
const AUTOMATION_LOGS_NOT_FOUND_MESSAGE =
  "No logs found for the selected OctoBots"

async function buildAuthHeader(): Promise<string> {
  const username = localStorage.getItem("auth_username") || "node"
  const password = (await loadPassword()) ?? ""
  return `Basic ${btoa(`${username}:${password}`)}`
}

function buildLogsTimestamp(): string {
  return new Date()
    .toISOString()
    .replace(/[-:]/g, "")
    .replace(/\..+/, "")
    .slice(0, 13)
}

/** Timestamped name for the downloaded node logs archive. */
export function buildNodeLogsArchiveFilename(): string {
  return `node-logs-${buildLogsTimestamp()}.zip`
}

/** Timestamped name for workflow / multi-task logs archives. */
export function buildWorkflowLogsExportFilename(): string {
  return `workflow-logs-${buildLogsTimestamp()}.zip`
}

/** Timestamped name for a single automation logs archive. */
export function buildAutomationLogsArchiveFilename(
  automationName: string,
  automationId: string,
): string {
  const safeName =
    automationName.replace(/[^a-z0-9\-_]/gi, "_").substring(0, 40) ||
    automationId.replace(/[^a-z0-9\-_]/gi, "_").substring(0, 40) ||
    "automation"
  return `automation-logs-${safeName}-${buildLogsTimestamp()}.zip`
}

async function fetchLogsZip(
  body: object,
  notFoundMessage: string,
  archiveName: string,
): Promise<{ bytes: Uint8Array; name: string; mime: string }> {
  const res = await fetch("/api/v1/logs/export", {
    method: "POST",
    headers: {
      Authorization: await buildAuthHeader(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  })
  if (res.status === 404) {
    throw new Error(notFoundMessage)
  }
  if (!res.ok) {
    throw new Error(`Failed to fetch logs (${res.status})`)
  }
  const buffer = await res.arrayBuffer()
  return {
    bytes: new Uint8Array(buffer),
    name: archiveName,
    mime: LOGS_ZIP_MIME,
  }
}

/** Fetch top-level node log files from the API as a zip ready to save. */
export async function fetchNodeLogsArchive(): Promise<{
  bytes: Uint8Array
  name: string
  mime: string
}> {
  return fetchLogsZip({}, NODE_LOGS_NOT_FOUND_MESSAGE, buildNodeLogsArchiveFilename())
}

/** Fetch per-automation log files for the given task ids. */
export async function fetchAutomationLogsArchive(
  taskIds: string[],
  archiveName: string,
): Promise<{ bytes: Uint8Array; name: string; mime: string }> {
  return fetchLogsZip(
    { task_ids: taskIds },
    AUTOMATION_LOGS_NOT_FOUND_MESSAGE,
    archiveName,
  )
}

export function downloadBytesAsFile(
  bytes: Uint8Array,
  filename: string,
  mime: string,
): void {
  const blob = new Blob([bytes as unknown as BlobPart], { type: mime })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = filename.replace(/[^a-z0-9\-_.]/gi, "_").substring(0, 255)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/** Fetch and trigger a browser download of the node logs archive. */
export async function downloadNodeLogsArchive(): Promise<void> {
  const archive = await fetchNodeLogsArchive()
  downloadBytesAsFile(archive.bytes, archive.name, archive.mime)
}

/** Fetch and trigger a browser download of one automation's logs archive. */
export async function downloadAutomationLogsArchive(
  taskId: string,
  automationName: string,
): Promise<void> {
  const archive = await fetchAutomationLogsArchive(
    [taskId],
    buildAutomationLogsArchiveFilename(automationName, taskId),
  )
  downloadBytesAsFile(archive.bytes, archive.name, archive.mime)
}
