import type { AutomationSignalType, UserAction } from "@/client"
import { signalTypeRequiresPayload } from "@/lib/debug/automation"
import {
  type SignalActionsPayloadFormat,
  parseSignalActionsPayloadText,
} from "@/lib/debug/signal-payload"

export type BuildSignalUserActionConfigurationResult =
  | { configuration: UserAction["configuration"] }
  | { error: string }

export function buildSignalUserActionConfiguration(
  automationId: string,
  signalType: AutomationSignalType,
  payloadText?: string,
  payloadFormat: SignalActionsPayloadFormat = "dsl_json",
): BuildSignalUserActionConfigurationResult {
  const configuration = {
    action_type: "automation_signal",
    automation_id: automationId,
    signal_type: signalType,
  } as UserAction["configuration"]

  if (!signalTypeRequiresPayload(signalType)) {
    return { configuration }
  }

  if (payloadText == null || !payloadText.trim()) {
    return { error: "Signal payload is required for this signal type." }
  }

  if (signalType === "actions") {
    const parseResult = parseSignalActionsPayloadText(payloadFormat, payloadText)
    if ("error" in parseResult) {
      return { error: parseResult.error }
    }
    ;(configuration as Record<string, unknown>).signal_payload =
      parseResult.signal_payload
    return { configuration }
  }

  try {
    const parsed = JSON.parse(payloadText) as unknown
    ;(configuration as Record<string, unknown>).signal_payload = parsed
    return { configuration }
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Invalid JSON",
    }
  }
}
