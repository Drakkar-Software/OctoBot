import { describe, expect, it } from "vitest"

import {
  buildDefaultDslActionsSignalPayload,
  defaultSignalActionsPayloadText,
  KEY_VAL_SIGNAL_PRESET_BUY,
  KEY_VAL_SIGNAL_PRESET_CANCEL,
  parseSignalActionsPayloadText,
} from "@/lib/debug/signal-payload"

const PRIORITY_ACTION_ID_PATTERN =
  /^action_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

describe("defaultSignalActionsPayloadText", () => {
  it("returns DSL JSON for dsl_json format", () => {
    const payloadText = defaultSignalActionsPayloadText("dsl_json")
    expect(payloadText).toContain("dsl_script")
    expect(payloadText).toContain("dsl_placeholder()")
    const parsed = JSON.parse(payloadText) as Array<{
      id: string
      dsl_script: string
    }>
    expect(parsed).toHaveLength(1)
    expect(parsed[0].dsl_script).toBe("dsl_placeholder()")
    expect(parsed[0].id).toMatch(PRIORITY_ACTION_ID_PATTERN)
  })

  it("generates a new priority action id on each call", () => {
    const firstPayload = JSON.parse(buildDefaultDslActionsSignalPayload()) as Array<{
      id: string
    }>
    const secondPayload = JSON.parse(buildDefaultDslActionsSignalPayload()) as Array<{
      id: string
    }>
    expect(firstPayload[0].id).not.toBe(secondPayload[0].id)
  })

  it("returns key=value lines for key_val_script format", () => {
    expect(defaultSignalActionsPayloadText("key_val_script")).toContain("SIGNAL=buy")
  })
})

describe("parseSignalActionsPayloadText", () => {
  it("parses DSL JSON array payloads", () => {
    const result = parseSignalActionsPayloadText(
      "dsl_json",
      '[{"id":"action_1","dsl_script":"noop()"}]',
    )
    expect("signal_payload" in result).toBe(true)
    if ("signal_payload" in result) {
      expect(result.signal_payload).toEqual([
        { id: "action_1", dsl_script: "noop()" },
      ])
    }
  })

  it("wraps plain key=value text as a script action", () => {
    const result = parseSignalActionsPayloadText(
      "key_val_script",
      "SYMBOL=BTC/USDC\nSIGNAL=buy\nVOLUME=0.00001",
    )
    expect("signal_payload" in result).toBe(true)
    if ("signal_payload" in result) {
      expect(result.signal_payload).toEqual([
        {
          script: "SYMBOL=BTC/USDC\nSIGNAL=buy\nVOLUME=0.00001",
        },
      ])
    }
  })

  it("parses multi-action JSON with script keys in key_val_script mode", () => {
    const result = parseSignalActionsPayloadText(
      "key_val_script",
      `[
        {"script": "SYMBOL=BTC/USDC\\nSIGNAL=buy"},
        {"script": "SYMBOL=BTC/USDC\\nSIGNAL=cancel"}
      ]`,
    )
    expect("signal_payload" in result).toBe(true)
    if ("signal_payload" in result) {
      expect(result.signal_payload).toEqual([
        { script: "SYMBOL=BTC/USDC\nSIGNAL=buy" },
        { script: "SYMBOL=BTC/USDC\nSIGNAL=cancel" },
      ])
    }
  })

  it("returns an error for invalid DSL JSON", () => {
    const result = parseSignalActionsPayloadText("dsl_json", "{")
    expect(result).toEqual({ error: expect.any(String) })
  })

  it("returns an error for empty payload text", () => {
    expect(parseSignalActionsPayloadText("dsl_json", "  ")).toEqual({
      error: "Signal payload is required for this signal type.",
    })
  })
})

describe("key val signal presets", () => {
  it("defines buy and cancel preset scripts", () => {
    expect(KEY_VAL_SIGNAL_PRESET_BUY).toContain("SIGNAL=buy")
    expect(KEY_VAL_SIGNAL_PRESET_BUY).toContain("VOLUME=20q")
    expect(KEY_VAL_SIGNAL_PRESET_BUY).not.toContain("TAKE_PROFIT")
    expect(KEY_VAL_SIGNAL_PRESET_CANCEL).toContain("SIGNAL=cancel")
  })
})
