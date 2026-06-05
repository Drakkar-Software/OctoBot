import { FileText } from "lucide-react"

import {
  formatImportedSnapshotContents,
  type ImportedDebugSummary,
} from "@/lib/debug/import"
import { formatDateTime } from "@/lib/format-datetime"

type ImportedDebugSnapshotBannerProps = {
  summary: ImportedDebugSummary
  onReturnToLive: () => void
}

export function ImportedDebugSnapshotBanner({
  summary,
}: ImportedDebugSnapshotBannerProps) {
  const latestUpdatedLabel = summary.latestStateUpdatedAt
    ? formatDateTime(summary.latestStateUpdatedAt)
    : "—"

  return (
    <div className="flex flex-col gap-4 rounded-md border border-frost/30 bg-frost/10 p-4 text-sm sm:flex-row sm:items-start">
      <FileText className="mt-0.5 size-4 shrink-0 text-frost" />
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <p className="font-medium text-foreground">
          Imported debug snapshot (read-only)
        </p>
        <p className="text-muted-foreground">
          You are viewing a static JSON snapshot from another user&apos;s node.
          This is not live data and nothing you do here is sent to the scheduler.
          Row actions open the user-action editor so you can copy JSON to send
          back to the user.
        </p>
        <ul className="space-y-1 font-mono text-xs text-muted-foreground">
          <li>Last updated in snapshot: {latestUpdatedLabel}</li>
          <li>Imported: {formatDateTime(summary.importedAt.toISOString())}</li>
          <li>Source: {summary.sourceLabel}</li>
          <li>State schema version: {summary.version}</li>
          <li>Contents: {formatImportedSnapshotContents(summary.counts)}</li>
        </ul>
      </div>
    </div>
  )
}
