import { describe, expect, it } from "vitest"

import {
  BASE_ACTION_TEMPLATES,
  TRADE_TEMPLATE,
  CANCEL_TEMPLATE,
  WITHDRAW_TEMPLATE,
  DEPOSIT_TEMPLATE,
  TRANSFER_TEMPLATE,
  WAIT_TEMPLATE,
  LOOP_UNTIL_ORDER_CLOSED_TEMPLATE,
  LOOP_UNTIL_BLOCKCHAIN_BALANCE_TEMPLATE,
  isParamValueValid,
} from "../action-templates"
import {
  getTemplateById,
} from "../meta-templates"

// ── Helpers ────────────────────────────────────────────────────────────────────

/** Simulate the validation from ReviewStep.tsx */
function validateAction(
  templateId: string,
  paramValues: Record<string, string>,
): { isValid: boolean; missingParams: string[] } {
  const template = getTemplateById(templateId)
  if (!template) return { isValid: false, missingParams: ["Unknown template"] }
  const missingParams = template.params
    .filter((p) => p.required && !isParamValueValid(p, paramValues[p.key]))
    .map((p) => p.label)
  return { isValid: missingParams.length === 0, missingParams }
}

/** Simulate the task content serialisation from EncryptStep.buildContentString */
function buildTaskContent(
  templateId: string,
  paramValues: Record<string, string>,
): Record<string, string> {
  const template = getTemplateById(templateId)
  const actions = template?.actionTypes.join(",") ?? ""
  return JSON.parse(JSON.stringify({ ...paramValues, ACTIONS: actions }))
}

// ── Registry ───────────────────────────────────────────────────────────────────

describe("action-templates", () => {
  describe("template registry", () => {
    it("contains all base templates", () => {
      expect(BASE_ACTION_TEMPLATES).toHaveLength(8)
    })

    it("each template has a unique id", () => {
      const ids = BASE_ACTION_TEMPLATES.map((t) => t.id)
      expect(new Set(ids).size).toBe(ids.length)
    })

    it("each template has at least one param and at least one actionType", () => {
      for (const template of BASE_ACTION_TEMPLATES) {
        expect(template.params.length).toBeGreaterThan(0)
        expect(template.actionTypes.length).toBeGreaterThan(0)
      }
    })

    it("each template has required fields", () => {
      for (const template of BASE_ACTION_TEMPLATES) {
        expect(template.id).toBeTruthy()
        expect(template.label).toBeTruthy()
        expect(template.description).toBeTruthy()
      }
    })
  })

  // ── getTemplateById ──────────────────────────────────────────────────────────

  describe("getTemplateById", () => {
    it("returns correct template by id", () => {
      expect(getTemplateById("trade")).toBe(TRADE_TEMPLATE)
      expect(getTemplateById("cancel")).toBe(CANCEL_TEMPLATE)
      expect(getTemplateById("withdraw")).toBe(WITHDRAW_TEMPLATE)
      expect(getTemplateById("deposit")).toBe(DEPOSIT_TEMPLATE)
      expect(getTemplateById("transfer")).toBe(TRANSFER_TEMPLATE)
      expect(getTemplateById("wait")).toBe(WAIT_TEMPLATE)
      expect(getTemplateById("loop_until_order_closed")).toBe(
        LOOP_UNTIL_ORDER_CLOSED_TEMPLATE,
      )
      expect(getTemplateById("loop_until_blockchain_balance")).toBe(
        LOOP_UNTIL_BLOCKCHAIN_BALANCE_TEMPLATE,
      )
    })

    it("returns undefined for unknown id", () => {
      expect(getTemplateById("nonexistent")).toBeUndefined()
    })
  })

  // ── Action keywords ──────────────────────────────────────────────────────────

  describe("action keywords (actionTypes)", () => {
    it("single-action templates declare exactly one keyword", () => {
      expect(TRADE_TEMPLATE.actionTypes).toEqual(["trade"])
      expect(CANCEL_TEMPLATE.actionTypes).toEqual(["cancel"])
      expect(WITHDRAW_TEMPLATE.actionTypes).toEqual(["withdraw"])
      expect(DEPOSIT_TEMPLATE.actionTypes).toEqual(["deposit"])
      expect(TRANSFER_TEMPLATE.actionTypes).toEqual(["transfer"])
      expect(WAIT_TEMPLATE.actionTypes).toEqual(["wait"])
      expect(LOOP_UNTIL_ORDER_CLOSED_TEMPLATE.actionTypes).toEqual([
        "loop_until_order_closed",
      ])
      expect(LOOP_UNTIL_BLOCKCHAIN_BALANCE_TEMPLATE.actionTypes).toEqual([
        "loop_until_blockchain_balance",
      ])
    })

    it("actionTypes values only use known keywords", () => {
      const known = new Set([
        "trade",
        "cancel",
        "withdraw",
        "deposit",
        "transfer",
        "wait",
        "loop_until_order_closed",
        "loop_until_blockchain_balance",
      ])
      for (const template of BASE_ACTION_TEMPLATES) {
        for (const keyword of template.actionTypes) {
          expect(known.has(keyword)).toBe(true)
        }
      }
    })
  })

  // ── Task content building ────────────────────────────────────────────────────

  describe("task content building", () => {
    it("trade content includes ACTIONS=trade and all param keys", () => {
      const content = buildTaskContent("trade", {
        ORDER_SYMBOL: "BTC/USDT",
        ORDER_AMOUNT: "0.5",
        ORDER_TYPE: "market",
        ORDER_SIDE: "buy",
        EXCHANGE_TO: "binance",
      })
      expect(content.ACTIONS).toBe("trade")
      expect(content.ORDER_SYMBOL).toBe("BTC/USDT")
      expect(content.ORDER_AMOUNT).toBe("0.5")
      expect(content.ORDER_TYPE).toBe("market")
    })

    it("cancel content includes ACTIONS=cancel", () => {
      const content = buildTaskContent("cancel", { ORDER_SYMBOL: "ETH/USDT" })
      expect(content.ACTIONS).toBe("cancel")
    })

    it("transfer content includes ACTIONS=transfer with source and destination keys", () => {
      const content = buildTaskContent("transfer", {
        BLOCKCHAIN_FROM_ASSET: "ETH",
        BLOCKCHAIN_FROM_AMOUNT: "1.0",
        BLOCKCHAIN_FROM: "ethereum",
        BLOCKCHAIN_TO_ADDRESS: "0x9876ABCDEF1234567890abcdef1234567890ABCD",
      })
      expect(content.ACTIONS).toBe("transfer")
      expect(content.BLOCKCHAIN_FROM_ASSET).toBe("ETH")
      expect(content.BLOCKCHAIN_TO_ADDRESS).toBe("0x9876ABCDEF1234567890abcdef1234567890ABCD")
    })

    it("withdraw content includes ACTIONS=withdraw", () => {
      const content = buildTaskContent("withdraw", {
        BLOCKCHAIN_TO_ASSET: "ETH",
        BLOCKCHAIN_TO: "ethereum",
        BLOCKCHAIN_TO_ADDRESS: "0x1234567890123456789012345678901234567890",
      })
      expect(content.ACTIONS).toBe("withdraw")
    })

    it("deposit content includes ACTIONS=deposit", () => {
      const content = buildTaskContent("deposit", {
        BLOCKCHAIN_FROM_ASSET: "BTC",
        BLOCKCHAIN_FROM_AMOUNT: "0.1",
        BLOCKCHAIN_FROM: "bitcoin",
        EXCHANGE_TO: "binance",
      })
      expect(content.ACTIONS).toBe("deposit")
    })

    it("wait content includes ACTIONS=wait and preserves delay values", () => {
      const content = buildTaskContent("wait", { MIN_DELAY: "30", MAX_DELAY: "60" })
      expect(content.ACTIONS).toBe("wait")
      expect(content.MIN_DELAY).toBe("30")
      expect(content.MAX_DELAY).toBe("60")
    })

    it("loop_until_order_closed content includes ACTIONS and loop params", () => {
      const content = buildTaskContent("loop_until_order_closed", {
        ORDER_EXCHANGE_ID: "ex-123",
        ORDER_SYMBOL: "BTC/USDT",
        LOOP_INTERVAL: "5",
        LOOP_TIMEOUT: "300",
        LOOP_MAX_ATTEMPTS: "10",
      })
      expect(content.ACTIONS).toBe("loop_until_order_closed")
      expect(content.ORDER_EXCHANGE_ID).toBe("ex-123")
      expect(content.LOOP_INTERVAL).toBe("5")
    })

    it("loop_until_blockchain_balance content includes ACTIONS and balance params", () => {
      const content = buildTaskContent("loop_until_blockchain_balance", {
        BLOCKCHAIN_BALANCE_ASSET: "ETH",
        BLOCKCHAIN_BALANCE: "ethereum",
        BLOCKCHAIN_BALANCE_ADDRESS: "0x1234567890123456789012345678901234567890",
        BLOCKCHAIN_BALANCE_AMOUNT: "1.0",
        LOOP_INTERVAL: "10",
      })
      expect(content.ACTIONS).toBe("loop_until_blockchain_balance")
      expect(content.BLOCKCHAIN_BALANCE_ASSET).toBe("ETH")
      expect(content.BLOCKCHAIN_BALANCE_AMOUNT).toBe("1.0")
    })

    it("sensitive params are included in content (not stripped)", () => {
      const content = buildTaskContent("deposit", {
        BLOCKCHAIN_FROM_ASSET: "BTC",
        BLOCKCHAIN_FROM_AMOUNT: "0.1",
        BLOCKCHAIN_FROM: "bitcoin",
        BLOCKCHAIN_FROM_PRIVATE_KEY: "a".repeat(64),
        EXCHANGE_TO: "binance",
      })
      expect(content.BLOCKCHAIN_FROM_PRIVATE_KEY).toBe("a".repeat(64))
    })
  })

  // ── Validation (mirrors ReviewStep logic) ────────────────────────────────────

  describe("action validation", () => {
    it("trade action with all required params is valid", () => {
      const { isValid, missingParams } = validateAction("trade", {
        ORDER_SYMBOL: "BTC/USDT",
        ORDER_AMOUNT: "0.5",
        ORDER_TYPE: "market",
      })
      expect(isValid).toBe(true)
      expect(missingParams).toHaveLength(0)
    })

    it("trade action missing ORDER_AMOUNT is invalid", () => {
      const { isValid, missingParams } = validateAction("trade", {
        ORDER_SYMBOL: "BTC/USDT",
        ORDER_TYPE: "market",
      })
      expect(isValid).toBe(false)
      expect(missingParams).toContain("Order Amount")
    })

    it("trade action with non-numeric ORDER_AMOUNT is invalid", () => {
      // CSV mapping may stash a non-numeric string in a number field; the
      // <input type=number> silently hides it so the UI must still flag it.
      const { isValid, missingParams } = validateAction("trade", {
        ORDER_SYMBOL: "BTC/USDT",
        ORDER_AMOUNT: "not-a-number",
        ORDER_TYPE: "market",
      })
      expect(isValid).toBe(false)
      expect(missingParams).toContain("Order Amount")
    })

    it("trade action missing ORDER_SYMBOL and ORDER_TYPE reports both", () => {
      const { isValid, missingParams } = validateAction("trade", {
        ORDER_AMOUNT: "0.5",
      })
      expect(isValid).toBe(false)
      expect(missingParams).toHaveLength(2)
    })

    it("cancel action with ORDER_SYMBOL only is valid", () => {
      const { isValid } = validateAction("cancel", { ORDER_SYMBOL: "ETH/USDT" })
      expect(isValid).toBe(true)
    })

    it("cancel action with empty ORDER_SYMBOL is invalid", () => {
      const { isValid, missingParams } = validateAction("cancel", { ORDER_SYMBOL: "  " })
      expect(isValid).toBe(false)
      expect(missingParams).toContain("Symbol")
    })

    it("wait action with MIN_DELAY is valid", () => {
      const { isValid } = validateAction("wait", { MIN_DELAY: "5" })
      expect(isValid).toBe(true)
    })

    it("wait action without MIN_DELAY is invalid", () => {
      const { isValid, missingParams } = validateAction("wait", {})
      expect(isValid).toBe(false)
      expect(missingParams).toContain("Wait Min Delay (s)")
    })

    it("deposit action requires asset, amount, network and exchange", () => {
      const { isValid: noParams } = validateAction("deposit", {})
      expect(noParams).toBe(false)

      const { isValid: allRequired } = validateAction("deposit", {
        BLOCKCHAIN_FROM_ASSET: "ETH",
        BLOCKCHAIN_FROM_AMOUNT: "1.0",
        BLOCKCHAIN_FROM: "ethereum",
        EXCHANGE_TO: "binance",
      })
      expect(allRequired).toBe(true)
    })

    it("transfer action requires source network, asset, amount, and destination address", () => {
      const { isValid: noParams } = validateAction("transfer", {})
      expect(noParams).toBe(false)

      const { isValid: allRequired } = validateAction("transfer", {
        BLOCKCHAIN_FROM_ASSET: "ETH",
        BLOCKCHAIN_FROM_AMOUNT: "1.0",
        BLOCKCHAIN_FROM: "ethereum",
        BLOCKCHAIN_TO_ADDRESS: "0x1234567890123456789012345678901234567890",
      })
      expect(allRequired).toBe(true)
    })

    it("withdraw action requires asset, network, and destination address", () => {
      const { isValid: allRequired } = validateAction("withdraw", {
        BLOCKCHAIN_TO_ASSET: "ETH",
        BLOCKCHAIN_TO: "ethereum",
        BLOCKCHAIN_TO_ADDRESS: "0x1234567890123456789012345678901234567890",
      })
      expect(allRequired).toBe(true)
    })

    it("loop_until_order_closed requires exchange id, symbol, and loop interval", () => {
      const { isValid: empty } = validateAction("loop_until_order_closed", {})
      expect(empty).toBe(false)

      const { isValid: ok } = validateAction("loop_until_order_closed", {
        ORDER_EXCHANGE_ID: "ord-1",
        ORDER_SYMBOL: "BTC/USDT",
        LOOP_INTERVAL: "5",
      })
      expect(ok).toBe(true)
    })

    it("loop_until_blockchain_balance requires asset, chain, address, amount, and interval", () => {
      const { isValid: empty } = validateAction(
        "loop_until_blockchain_balance",
        {},
      )
      expect(empty).toBe(false)

      const { isValid: ok } = validateAction("loop_until_blockchain_balance", {
        BLOCKCHAIN_BALANCE_ASSET: "ETH",
        BLOCKCHAIN_BALANCE: "ethereum",
        BLOCKCHAIN_BALANCE_ADDRESS:
          "0x1234567890123456789012345678901234567890",
        BLOCKCHAIN_BALANCE_AMOUNT: "1",
        LOOP_INTERVAL: "5",
      })
      expect(ok).toBe(true)
    })

    it("unknown templateId is always invalid", () => {
      const { isValid, missingParams } = validateAction("unknown", { anything: "value" })
      expect(isValid).toBe(false)
      expect(missingParams).toContain("Unknown template")
    })

    it("optional params being absent does not affect validity", () => {
      // TRADE has many optional params (ORDER_SIDE, ORDER_PRICE, etc.)
      const { isValid } = validateAction("trade", {
        ORDER_SYMBOL: "SOL/USDT",
        ORDER_AMOUNT: "10",
        ORDER_TYPE: "limit",
        // ORDER_SIDE, ORDER_PRICE, EXCHANGE_TO, etc. intentionally absent
      })
      expect(isValid).toBe(true)
    })
  })

  // ── Per-template param schemas ───────────────────────────────────────────────

  describe("TRADE_TEMPLATE", () => {
    it("requires ORDER_SYMBOL, ORDER_AMOUNT, and ORDER_TYPE", () => {
      const required = TRADE_TEMPLATE.params.filter((p) => p.required).map((p) => p.key)
      expect(required).toContain("ORDER_SYMBOL")
      expect(required).toContain("ORDER_AMOUNT")
      expect(required).toContain("ORDER_TYPE")
    })

    it("has trading pair detection on ORDER_SYMBOL", () => {
      const patterns = TRADE_TEMPLATE.params.find((p) => p.key === "ORDER_SYMBOL")!.detectPatterns!
      expect(patterns.some((p) => p.test("BTC/USDT"))).toBe(true)
      expect(patterns.some((p) => p.test("notapair"))).toBe(false)
    })

    it("marks API_KEY and API_SECRET as sensitive", () => {
      const apiKey = TRADE_TEMPLATE.params.find((p) => p.key === "API_KEY")
      const apiSecret = TRADE_TEMPLATE.params.find((p) => p.key === "API_SECRET")
      expect(apiKey?.sensitive).toBe(true)
      expect(apiSecret?.sensitive).toBe(true)
    })
  })

  describe("CANCEL_TEMPLATE", () => {
    it("has exactly one required param: ORDER_SYMBOL", () => {
      const required = CANCEL_TEMPLATE.params.filter((p) => p.required).map((p) => p.key)
      expect(required).toEqual(["ORDER_SYMBOL"])
    })

    it("has order side detection", () => {
      const patterns = CANCEL_TEMPLATE.params.find((p) => p.key === "ORDER_SIDE")!.detectPatterns!
      expect(patterns.some((p) => p.test("buy"))).toBe(true)
      expect(patterns.some((p) => p.test("sell"))).toBe(true)
    })
  })

  describe("WITHDRAW_TEMPLATE", () => {
    it("requires asset, network, and destination address", () => {
      const required = WITHDRAW_TEMPLATE.params.filter((p) => p.required).map((p) => p.key)
      expect(required).toContain("BLOCKCHAIN_TO_ASSET")
      expect(required).toContain("BLOCKCHAIN_TO")
      expect(required).toContain("BLOCKCHAIN_TO_ADDRESS")
    })
  })

  describe("WAIT_TEMPLATE", () => {
    it("requires MIN_DELAY only; MAX_DELAY is optional", () => {
      const required = WAIT_TEMPLATE.params.filter((p) => p.required).map((p) => p.key)
      expect(required).toEqual(["MIN_DELAY"])
    })

    it("has numeric detection on MIN_DELAY", () => {
      const patterns = WAIT_TEMPLATE.params.find((p) => p.key === "MIN_DELAY")!.detectPatterns!
      expect(patterns.some((p) => p.test("10"))).toBe(true)
      expect(patterns.some((p) => p.test("3.5"))).toBe(true)
      expect(patterns.some((p) => p.test("abc"))).toBe(false)
    })
  })

  describe("LOOP_UNTIL_ORDER_CLOSED_TEMPLATE", () => {
    it("requires exchange order id, symbol, and loop interval", () => {
      const required = LOOP_UNTIL_ORDER_CLOSED_TEMPLATE.params
        .filter((p) => p.required)
        .map((p) => p.key)
      expect(required).toEqual([
        "ORDER_EXCHANGE_ID",
        "ORDER_SYMBOL",
        "LOOP_INTERVAL",
      ])
    })

    it("shares loop timeout and max attempts params with blockchain balance loop", () => {
      const keys = LOOP_UNTIL_ORDER_CLOSED_TEMPLATE.params.map((p) => p.key)
      expect(keys).toContain("LOOP_TIMEOUT")
      expect(keys).toContain("LOOP_MAX_ATTEMPTS")
    })
  })

  describe("LOOP_UNTIL_BLOCKCHAIN_BALANCE_TEMPLATE", () => {
    it("requires balance target fields and loop interval", () => {
      const required = LOOP_UNTIL_BLOCKCHAIN_BALANCE_TEMPLATE.params
        .filter((p) => p.required)
        .map((p) => p.key)
      expect(required).toEqual([
        "BLOCKCHAIN_BALANCE_ASSET",
        "BLOCKCHAIN_BALANCE",
        "BLOCKCHAIN_BALANCE_ADDRESS",
        "BLOCKCHAIN_BALANCE_AMOUNT",
        "LOOP_INTERVAL",
      ])
    })

    it("has address detection on BLOCKCHAIN_BALANCE_ADDRESS", () => {
      const patterns = LOOP_UNTIL_BLOCKCHAIN_BALANCE_TEMPLATE.params.find(
        (p) => p.key === "BLOCKCHAIN_BALANCE_ADDRESS",
      )!.detectPatterns!
      expect(
        patterns.some((p) =>
          p.test("0x1234567890123456789012345678901234567890"),
        ),
      ).toBe(true)
    })
  })

  describe("DEPOSIT_TEMPLATE", () => {
    it("requires asset, amount, network, and destination exchange", () => {
      const required = DEPOSIT_TEMPLATE.params.filter((p) => p.required).map((p) => p.key)
      expect(required).toContain("BLOCKCHAIN_FROM_ASSET")
      expect(required).toContain("BLOCKCHAIN_FROM_AMOUNT")
      expect(required).toContain("BLOCKCHAIN_FROM")
      expect(required).toContain("EXCHANGE_TO")
    })

    it("exposes optional signing and block height params for deposit flow", () => {
      const keys = DEPOSIT_TEMPLATE.params.map((p) => p.key)
      expect(keys).toContain("BLOCKCHAIN_FROM_PRIVATE_KEY")
      expect(keys).toContain("BLOCKCHAIN_FROM_MNEMONIC_SEED")
      expect(keys).toContain("BLOCKCHAIN_FROM_BLOCK_HEIGHT")
    })

    it("marks private key and mnemonic as sensitive password fields", () => {
      const pk = DEPOSIT_TEMPLATE.params.find((p) => p.key === "BLOCKCHAIN_FROM_PRIVATE_KEY")!
      const mnemonic = DEPOSIT_TEMPLATE.params.find((p) => p.key === "BLOCKCHAIN_FROM_MNEMONIC_SEED")!
      expect(pk.sensitive).toBe(true)
      expect(pk.type).toBe("password")
      expect(mnemonic.sensitive).toBe(true)
      expect(mnemonic.type).toBe("password")
    })
  })

  describe("TRANSFER_TEMPLATE", () => {
    it("requires source chain, asset, amount, and destination address", () => {
      const required = TRANSFER_TEMPLATE.params.filter((p) => p.required).map((p) => p.key)
      expect(required).toContain("BLOCKCHAIN_FROM")
      expect(required).toContain("BLOCKCHAIN_FROM_ASSET")
      expect(required).toContain("BLOCKCHAIN_FROM_AMOUNT")
      expect(required).toContain("BLOCKCHAIN_TO_ADDRESS")
    })

    it("exposes optional signing params and block height", () => {
      const keys = TRANSFER_TEMPLATE.params.map((p) => p.key)
      expect(keys).toContain("BLOCKCHAIN_FROM_PRIVATE_KEY")
      expect(keys).toContain("BLOCKCHAIN_FROM_MNEMONIC_SEED")
      expect(keys).toContain("BLOCKCHAIN_FROM_BLOCK_HEIGHT")
    })

    it("has EVM and BTC address detection on BLOCKCHAIN_TO_ADDRESS", () => {
      const patterns = TRANSFER_TEMPLATE.params.find((p) => p.key === "BLOCKCHAIN_TO_ADDRESS")!.detectPatterns!
      expect(patterns.some((p) => p.test("0x1234567890123456789012345678901234567890"))).toBe(true)
      expect(patterns.some((p) => p.test("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"))).toBe(true)
      expect(patterns.some((p) => p.test("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"))).toBe(true)
    })

    it("marks private key as sensitive password field", () => {
      const pk = TRANSFER_TEMPLATE.params.find((p) => p.key === "BLOCKCHAIN_FROM_PRIVATE_KEY")!
      expect(pk.sensitive).toBe(true)
      expect(pk.type).toBe("password")
    })
  })

  describe("regex pattern edge cases", () => {
    it("tradingPair rejects single-char symbols and those exceeding 10 chars", () => {
      const pattern = TRADE_TEMPLATE.params.find((p) => p.key === "ORDER_SYMBOL")!.detectPatterns![0]
      expect(pattern.test("A/B")).toBe(false)
      expect(pattern.test("ABCDEFGHIJK/USDT")).toBe(false)
    })

    it("tradingPair matches case-insensitively", () => {
      const pattern = TRADE_TEMPLATE.params.find((p) => p.key === "ORDER_SYMBOL")!.detectPatterns![0]
      expect(pattern.test("btc/usdt")).toBe(true)
    })

    it("evmAddress rejects wrong-length hex addresses", () => {
      const pattern = TRANSFER_TEMPLATE.params.find((p) => p.key === "BLOCKCHAIN_TO_ADDRESS")!.detectPatterns![0]
      expect(pattern.test("0x123456789012345678901234567890123456789")).toBe(false)   // 39 hex
      expect(pattern.test("0x12345678901234567890123456789012345678901")).toBe(false) // 41 hex
    })

    it("privateKeyHex matches 64-char hex with or without 0x prefix", () => {
      const patterns = TRANSFER_TEMPLATE.params.find((p) => p.key === "BLOCKCHAIN_FROM_PRIVATE_KEY")!.detectPatterns!
      const key64 = "a".repeat(64)
      expect(patterns.some((p) => p.test(key64))).toBe(true)
      expect(patterns.some((p) => p.test("0x" + key64))).toBe(true)
      expect(patterns.some((p) => p.test("0x" + "g".repeat(64)))).toBe(false)
    })

    it("mnemonicSeed matches 12 and 24 word phrases, rejects short ones", () => {
      const patterns = TRANSFER_TEMPLATE.params.find((p) => p.key === "BLOCKCHAIN_FROM_MNEMONIC_SEED")!.detectPatterns!
      expect(patterns.some((p) => p.test(Array(12).fill("abandon").join(" ")))).toBe(true)
      expect(patterns.some((p) => p.test(Array(24).fill("abandon").join(" ")))).toBe(true)
      expect(patterns.some((p) => p.test("only three words"))).toBe(false)
    })

    it("exchange name matches known names case-insensitively, rejects unknowns", () => {
      const patterns = TRADE_TEMPLATE.params.find((p) => p.key === "EXCHANGE_TO")!.detectPatterns!
      for (const name of ["binance", "KRAKEN", "coinbase", "bybit", "okx"]) {
        expect(patterns.some((p) => p.test(name))).toBe(true)
      }
      expect(patterns.some((p) => p.test("myexchange"))).toBe(false)
    })

    it("numericAmount matches integers and decimals, rejects non-numeric", () => {
      const patterns = TRADE_TEMPLATE.params.find((p) => p.key === "ORDER_AMOUNT")!.detectPatterns!
      for (const v of ["100", "0.5", "-10", "0"]) {
        expect(patterns.some((p) => p.test(v))).toBe(true)
      }
      for (const v of ["abc", "1.2.3", "$100"]) {
        expect(patterns.some((p) => p.test(v))).toBe(false)
      }
    })

    it("orderSide matches buy/sell/long/short, rejects others", () => {
      const patterns = TRADE_TEMPLATE.params.find((p) => p.key === "ORDER_SIDE")!.detectPatterns!
      for (const v of ["buy", "sell", "long", "short", "BUY"]) {
        expect(patterns.some((p) => p.test(v))).toBe(true)
      }
      expect(patterns.some((p) => p.test("hold"))).toBe(false)
    })

    it("orderType matches known types, rejects unknowns", () => {
      const patterns = TRADE_TEMPLATE.params.find((p) => p.key === "ORDER_TYPE")!.detectPatterns!
      for (const v of ["market", "limit", "stop", "stop_limit", "trailing_stop"]) {
        expect(patterns.some((p) => p.test(v))).toBe(true)
      }
      expect(patterns.some((p) => p.test("oco"))).toBe(false)
    })
  })

  // ── Schema invariants ────────────────────────────────────────────────────────

  describe("schema invariants", () => {
    it("all select params have non-empty options arrays", () => {
      for (const template of BASE_ACTION_TEMPLATES) {
        for (const param of template.params) {
          if (param.type === "select") {
            expect(param.options).toBeDefined()
            expect(param.options!.length).toBeGreaterThan(0)
          }
        }
      }
    })

    it("each param with detectPatterns contains only RegExp instances", () => {
      for (const template of BASE_ACTION_TEMPLATES) {
        for (const param of template.params) {
          for (const pattern of param.detectPatterns ?? []) {
            expect(pattern).toBeInstanceOf(RegExp)
          }
        }
      }
    })

    it("each param with aliasFuzzy contains only non-empty strings", () => {
      for (const template of BASE_ACTION_TEMPLATES) {
        for (const param of template.params) {
          for (const alias of param.aliasFuzzy ?? []) {
            expect(alias.length).toBeGreaterThan(0)
          }
        }
      }
    })
  })
})
