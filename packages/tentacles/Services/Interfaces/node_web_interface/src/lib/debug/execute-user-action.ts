import type { AutomationSignalType, UserAction } from "@/client"
import { signalTypeRequiresPayload } from "@/lib/debug/automation"

export type BuildSignalUserActionConfigurationResult =
  | { configuration: UserAction["configuration"] }
  | { error: string }

export function buildSignalUserActionConfiguration(
  automationId: string,
  signalType: AutomationSignalType,
  payloadText?: string,
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
