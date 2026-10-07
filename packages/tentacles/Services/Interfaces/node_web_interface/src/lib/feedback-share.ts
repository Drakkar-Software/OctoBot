import {
  FeedbackService,
  type FeedbackPreviewResponse,
  type FeedbackUploadEnvelope,
} from "@/client"
import { downloadBytesAsFile } from "@/lib/logs-export"

export type ShareFeedbackFailureKind =
  | "boot_failed"
  | "auth_broken"
  | "fatal_render"
  | "insecure_context"

export type ShareFeedbackContext =
  | { source: "navbar" }
  | { source: "settings" }
  | { source: "recovery"; failureKind: ShareFeedbackFailureKind }
  | { source: "route_error"; routePath?: string }

export type ShareFeedbackContactMethod = "email" | "telegram" | "discord"

export type FeedbackExportRequestBody = {
  note: string | null
  issue_url: string | null
  ui_error_name: string | null
  ui_error_route: string | null
}

export type SubmitFeedbackDownloadResult =
  | { attachmentKind: "zip" }
  | { attachmentKind: "json"; envelope: FeedbackUploadEnvelope }

type JourneySummary = FeedbackPreviewResponse["journey_summary"]

type FirstFailureSummary = {
  event?: string
  timestamp?: number | null
  error_category?: string | null
  error_message?: string | null
}

type JournalEventLine = FeedbackUploadEnvelope["events"][number]

const FIRST_FAILURE_MESSAGE_MAX_LENGTH = 120
const RECONCILE_COMPLETED_EVENT = "reconcile_completed"
export const FEEDBACK_SUPPORT_EMAIL = "contact@octobot.cloud"
export const FEEDBACK_JOURNAL_ZIP_FILENAME = "node_journal.zip"
export const FEEDBACK_JOURNAL_JSON_FILENAME = "node_journal.json"
const FEEDBACK_JOURNAL_ZIP_MIME = "application/zip"
export const FEEDBACK_PREVIEW_UNAVAILABLE_MESSAGE =
  "Activity history couldn't be loaded. You can still download diagnostics and email your feedback below."

export async function fetchFeedbackPreview(): Promise<FeedbackPreviewResponse> {
  return FeedbackService.getFeedbackPreview()
}

export async function fetchFeedbackJournalZip(
  requestBody: FeedbackExportRequestBody,
): Promise<Uint8Array> {
  const res = await fetch("/api/v1/feedback/export", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(requestBody),
  })
  if (!res.ok) {
    throw new Error(`Failed to export feedback (${res.status})`)
  }
  const buffer = await res.arrayBuffer()
  return new Uint8Array(buffer)
}

export function getPreviewEventCount(preview: FeedbackPreviewResponse): number {
  return preview.upload_envelope.event_count
}

export function shouldUseDegradedFeedbackWithoutPreview({
  previewAuthBlocked,
  previewLoading,
  previewError,
}: {
  previewAuthBlocked: boolean
  previewLoading: boolean
  previewError: boolean
}): boolean {
  return previewError && !previewAuthBlocked && !previewLoading
}

export function computeShareFeedbackSendDisabled({
  submitPending,
  useDegradedFeedback,
  hasUiErrorContext,
  showSignInPrompt,
  previewLoading,
  previewError,
  hasPreview,
  eventCount,
  note,
}: {
  submitPending: boolean
  useDegradedFeedback: boolean
  hasUiErrorContext: boolean
  showSignInPrompt: boolean
  previewLoading: boolean
  previewError: boolean
  hasPreview: boolean
  eventCount: number | null
  note: string
}): boolean {
  if (submitPending) {
    return true
  }
  if (useDegradedFeedback) {
    return false
  }
  if (showSignInPrompt) {
    return true
  }
  if (previewLoading) {
    return true
  }
  if (previewError) {
    return true
  }
  if (!hasPreview) {
    return true
  }
  const isEmptyJournal = eventCount === 0
  if (isEmptyJournal && note.trim() === "") {
    return !hasUiErrorContext
  }
  return false
}

export function getShareFeedbackUiErrorName(
  context: ShareFeedbackContext,
): string | null {
  if (context.source === "recovery") {
    return context.failureKind
  }
  if (context.source === "route_error") {
    return "route_error"
  }
  return null
}

export type ShareFeedbackPageLocation = Pick<Location, "pathname">

export function resolveShareFeedbackUiErrorRoute(
  context: ShareFeedbackContext,
  location?: ShareFeedbackPageLocation | null,
): string | null {
  if (context.source === "route_error") {
    const routePath = context.routePath?.trim()
    if (routePath) {
      return routePath
    }
  }
  const pathname = location?.pathname?.trim()
  return pathname ? pathname : null
}

export function getPreviewAutomationCount(
  preview: FeedbackPreviewResponse,
): number | null {
  const events = preview.upload_envelope.events
  for (let eventIndex = events.length - 1; eventIndex >= 0; eventIndex -= 1) {
    const eventLine = events[eventIndex] as JournalEventLine
    if (eventLine.event !== RECONCILE_COMPLETED_EVENT) {
      continue
    }
    const attributes = eventLine.attributes as
      | { automation_count?: number }
      | undefined
    const automationCount = attributes?.automation_count
    if (typeof automationCount === "number") {
      return automationCount
    }
  }
  return null
}

export function buildContextNotePrefix(context: ShareFeedbackContext): string {
  if (context.source === "navbar") {
    return "[ui_context] source=navbar"
  }
  if (context.source === "settings") {
    return "[ui_context] source=settings"
  }
  if (context.source === "recovery") {
    return `[ui_context] source=recovery failure_kind=${context.failureKind}`
  }
  const routeSuffix =
    context.routePath !== undefined ? ` route=${context.routePath}` : ""
  return `[ui_context] source=route_error${routeSuffix}`
}

export function buildContactNoteSuffix({
  contactMethod,
  contactValue,
}: {
  contactMethod?: ShareFeedbackContactMethod
  contactValue?: string
}): string | null {
  const trimmedValue = contactValue?.trim() ?? ""
  if (!contactMethod && !trimmedValue) {
    return null
  }
  const methodSuffix = contactMethod ?? "unspecified"
  const valueSuffix = trimmedValue || "unspecified"
  return `[contact] method=${methodSuffix} value=${valueSuffix}`
}

export function buildFeedbackNote({
  note,
  context,
  contactMethod,
  contactValue,
}: {
  note?: string
  context: ShareFeedbackContext
  contactMethod?: ShareFeedbackContactMethod
  contactValue?: string
}): string {
  const noteParts: string[] = []
  if (getShareFeedbackUiErrorName(context) === null) {
    noteParts.push(buildContextNotePrefix(context))
  }
  const trimmedNote = note?.trim() ?? ""
  if (trimmedNote) {
    noteParts.push(trimmedNote)
  }
  const contactSuffix = buildContactNoteSuffix({
    contactMethod,
    contactValue,
  })
  if (contactSuffix) {
    noteParts.push(contactSuffix)
  }
  if (noteParts.length === 0) {
    return ""
  }
  return noteParts.join("\n\n")
}

function truncateText(value: string, maxLength: number): string {
  if (value.length <= maxLength) {
    return value
  }
  return `${value.slice(0, maxLength - 1)}…`
}

function formatFirstFailureTimestamp(timestamp: number | null | undefined): string {
  if (typeof timestamp !== "number" || !Number.isFinite(timestamp)) {
    return ""
  }
  return new Date(timestamp * 1000).toLocaleString()
}

function formatFirstFailureLine(firstFailure: FirstFailureSummary): string {
  const eventName = firstFailure.event ?? "unknown"
  const category = firstFailure.error_category?.trim()
  const message = firstFailure.error_message?.trim()
  const timestampLabel = formatFirstFailureTimestamp(firstFailure.timestamp)

  const detailParts: string[] = [eventName]
  if (category) {
    detailParts.push(category)
  }
  if (message) {
    detailParts.push(truncateText(message, FIRST_FAILURE_MESSAGE_MAX_LENGTH))
  }

  const detailText = detailParts.join(" — ")
  if (timestampLabel) {
    return `First failure (${timestampLabel}): ${detailText}`
  }
  return `First failure: ${detailText}`
}

export function formatJourneySummaryForDisplay(
  summary: JourneySummary,
): string[] {
  const displayLines: string[] = []

  if (typeof summary.onboarding_complete === "boolean") {
    displayLines.push(
      `Onboarding complete: ${summary.onboarding_complete ? "yes" : "no"}`,
    )
  }

  if (typeof summary.furthest_step_reached === "string" && summary.furthest_step_reached) {
    displayLines.push(`Furthest step: ${summary.furthest_step_reached}`)
  }

  if (typeof summary.ui_blocking_issues_count === "number") {
    displayLines.push(
      `UI blocking issues: ${summary.ui_blocking_issues_count}`,
    )
  }

  const firstFailure = summary.first_failure as FirstFailureSummary | null | undefined
  if (firstFailure && typeof firstFailure === "object") {
    displayLines.push(formatFirstFailureLine(firstFailure))
  }

  return displayLines
}

export function buildFeedbackFilename(_envelope: FeedbackUploadEnvelope): string {
  return FEEDBACK_JOURNAL_JSON_FILENAME
}

export function downloadFeedbackEnvelope(envelope: FeedbackUploadEnvelope): void {
  const jsonBody = JSON.stringify(envelope, null, 2)
  downloadBytesAsFile(
    new TextEncoder().encode(jsonBody),
    buildFeedbackFilename(envelope),
    "application/json",
  )
}

const CONTACT_METHOD_MAIL_LABELS: Record<ShareFeedbackContactMethod, string> = {
  email: "Email",
  telegram: "Telegram",
  discord: "Discord",
}

export function buildFeedbackMailtoUrl({
  note,
  contactMethod,
  contactValue,
  attachmentFilename = FEEDBACK_JOURNAL_ZIP_FILENAME,
}: {
  note?: string
  contactMethod?: ShareFeedbackContactMethod
  contactValue?: string
  attachmentFilename?: string
}): string {
  const bodyParts: string[] = [
    `REMINDER: Please attach the downloaded ${attachmentFilename} file to this email.`,
  ]
  const trimmedNote = note?.trim() ?? ""
  if (trimmedNote) {
    bodyParts.push(trimmedNote)
  }
  const trimmedContact = contactValue?.trim() ?? ""
  if (contactMethod || trimmedContact) {
    const methodLabel = contactMethod
      ? CONTACT_METHOD_MAIL_LABELS[contactMethod]
      : "Contact"
    bodyParts.push(
      trimmedContact
        ? `${methodLabel}: ${trimmedContact}`
        : `${methodLabel}: (not provided)`,
    )
  }
  const subject = "OctoBot Node feedback"
  const body = bodyParts.join("\n\n")
  const query = `subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
  return `mailto:${FEEDBACK_SUPPORT_EMAIL}?${query}`
}

export function openFeedbackMailto(mailtoUrl: string): void {
  if (typeof window === "undefined") {
    return
  }
  window.location.assign(mailtoUrl)
}

export function downloadPreviewEnvelope(preview: FeedbackPreviewResponse): void {
  downloadFeedbackEnvelope(preview.upload_envelope)
}

export function buildRecoveryFeedbackFallbackEnvelope({
  note,
  uiErrorName,
  uiErrorRoute,
}: {
  note: string
  uiErrorName: string | null
  uiErrorRoute: string | null
}): FeedbackUploadEnvelope {
  return {
    install_id: "recovery-client-fallback",
    app_version: "unknown",
    onboarding_started_at: null,
    onboarding_complete: false,
    journey_summary: {
      source: "recovery_client_fallback",
    },
    events: [],
    uploaded: false,
    ready: false,
    event_count: 0,
    note,
    ui_error_name: uiErrorName,
    ui_error_route: uiErrorRoute,
  }
}

export function buildRecoveryFeedbackFallback({
  note,
  uiErrorName,
  uiErrorRoute,
}: {
  note: string
  uiErrorName: string | null
  uiErrorRoute: string | null
}): FeedbackUploadEnvelope {
  return buildRecoveryFeedbackFallbackEnvelope({
    note,
    uiErrorName,
    uiErrorRoute,
  })
}

export function mergePreviewUploadEnvelopeForFallback({
  previewUploadEnvelope,
  composedNote,
  uiErrorName,
  uiErrorRoute,
}: {
  previewUploadEnvelope: FeedbackUploadEnvelope
  composedNote: string
  uiErrorName: string | null
  uiErrorRoute: string | null
}): FeedbackUploadEnvelope {
  return {
    ...previewUploadEnvelope,
    note: composedNote ? composedNote : previewUploadEnvelope.note ?? null,
    ui_error_name: uiErrorName,
    ui_error_route: uiErrorRoute,
  }
}

export async function submitFeedbackDownload({
  note,
  context,
  contactMethod,
  contactValue,
  previewUploadEnvelope,
}: {
  note?: string
  context: ShareFeedbackContext
  contactMethod?: ShareFeedbackContactMethod
  contactValue?: string
  previewUploadEnvelope?: FeedbackUploadEnvelope
}): Promise<SubmitFeedbackDownloadResult> {
  const pageLocation =
    typeof window !== "undefined" ? window.location : undefined
  const uiErrorName = getShareFeedbackUiErrorName(context)
  const uiErrorRoute = resolveShareFeedbackUiErrorRoute(context, pageLocation)
  const composedNote = buildFeedbackNote({
    note,
    context,
    contactMethod,
    contactValue,
  })
  const exportRequestBody: FeedbackExportRequestBody = {
    note: composedNote || null,
    issue_url: null,
    ui_error_name: uiErrorName,
    ui_error_route: uiErrorRoute,
  }
  const mailtoParams = {
    note,
    contactMethod,
    contactValue,
  }

  try {
    const zipBytes = await fetchFeedbackJournalZip(exportRequestBody)
    downloadBytesAsFile(
      zipBytes,
      FEEDBACK_JOURNAL_ZIP_FILENAME,
      FEEDBACK_JOURNAL_ZIP_MIME,
    )
    openFeedbackMailto(
      buildFeedbackMailtoUrl({
        ...mailtoParams,
        attachmentFilename: FEEDBACK_JOURNAL_ZIP_FILENAME,
      }),
    )
    return { attachmentKind: "zip" }
  } catch {
    const envelope = previewUploadEnvelope
      ? mergePreviewUploadEnvelopeForFallback({
          previewUploadEnvelope,
          composedNote,
          uiErrorName,
          uiErrorRoute,
        })
      : buildRecoveryFeedbackFallback({
          note: composedNote,
          uiErrorName,
          uiErrorRoute,
        })
    downloadFeedbackEnvelope(envelope)
    openFeedbackMailto(
      buildFeedbackMailtoUrl({
        ...mailtoParams,
        attachmentFilename: FEEDBACK_JOURNAL_JSON_FILENAME,
      }),
    )
    return { attachmentKind: "json", envelope }
  }
}
