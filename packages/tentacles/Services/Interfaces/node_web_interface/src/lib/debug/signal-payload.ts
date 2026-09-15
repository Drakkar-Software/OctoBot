export type SignalActionsPayloadFormat = "dsl_json" | "key_val_script"

function newPriorityActionId(): string {
  return `action_${crypto.randomUUID()}`
}

export function buildDefaultDslActionsSignalPayload(): string {
  return JSON.stringify(
    [
      {
        id: newPriorityActionId(),
        dsl_script: "dsl_placeholder()",
      },
    ],
    null,
    2,
  )
}

export const DEFAULT_KEY_VAL_ACTIONS_SIGNAL_PAYLOAD = `SYMBOL=BTC/USDC
SIGNAL=buy
VOLUME=20q`

export const KEY_VAL_SIGNAL_PRESET_BUY = DEFAULT_KEY_VAL_ACTIONS_SIGNAL_PAYLOAD

export const KEY_VAL_SIGNAL_PRESET_CANCEL = `SYMBOL=BTC/USDC
SIGNAL=cancel`

export type ParseSignalActionsPayloadTextResult =
  | { signal_payload: unknown }
  | { error: string }

export function defaultSignalActionsPayloadText(
  format: SignalActionsPayloadFormat,
): string {
  switch (format) {
    case "dsl_json":
      return buildDefaultDslActionsSignalPayload()
    case "key_val_script":
      return DEFAULT_KEY_VAL_ACTIONS_SIGNAL_PAYLOAD
    default: {
      const unexpectedFormat: never = format
      throw new Error(`Unexpected signal actions payload format: ${unexpectedFormat}`)
    }
  }
}

function parseJsonPayload(payloadText: string): ParseSignalActionsPayloadTextResult {
  try {
    return { signal_payload: JSON.parse(payloadText) as unknown }
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Invalid JSON",
    }
  }
}

export function parseSignalActionsPayloadText(
  format: SignalActionsPayloadFormat,
  payloadText: string,
): ParseSignalActionsPayloadTextResult {
  const trimmedPayloadText = payloadText.trim()
  if (!trimmedPayloadText) {
    return { error: "Signal payload is required for this signal type." }
  }

  if (format === "dsl_json") {
    return parseJsonPayload(trimmedPayloadText)
  }

  if (trimmedPayloadText.startsWith("[") || trimmedPayloadText.startsWith("{")) {
    return parseJsonPayload(trimmedPayloadText)
  }

  return {
    signal_payload: [{ script: trimmedPayloadText }],
  }
}
