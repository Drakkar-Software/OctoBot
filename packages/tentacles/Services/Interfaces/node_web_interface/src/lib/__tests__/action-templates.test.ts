import { describe, expect, it } from "vitest"

import {
  ACTION_TEMPLATES,
  getTemplateById,
  TRADE_TEMPLATE,
  CANCEL_TEMPLATE,
  WITHDRAW_TEMPLATE,
  DEPOSIT_TEMPLATE,
  TRANSFER_TEMPLATE,
  WAIT_TEMPLATE,
} from "../action-templates"

describe("action-templates", () => {
  describe("template registry", () => {
    it("contains all 6 templates", () => {
      expect(ACTION_TEMPLATES).toHaveLength(6)
    })

    it("each template has a unique id", () => {
      const ids = ACTION_TEMPLATES.map((t) => t.id)
      expect(new Set(ids).size).toBe(ids.length)
    })

    it("each template has at least one param", () => {
      for (const template of ACTION_TEMPLATES) {
        expect(template.params.length).toBeGreaterThan(0)
      }
    })

    it("each template has required fields", () => {
      for (const template of ACTION_TEMPLATES) {
        expect(template.id).toBeTruthy()
        expect(template.label).toBeTruthy()
        expect(template.description).toBeTruthy()
        expect(template.actionTypes.length).toBeGreaterThan(0)
      }
    })
  })

  describe("getTemplateById", () => {
    it("returns correct template by id", () => {
      expect(getTemplateById("trade")).toBe(TRADE_TEMPLATE)
      expect(getTemplateById("cancel")).toBe(CANCEL_TEMPLATE)
      expect(getTemplateById("withdraw")).toBe(WITHDRAW_TEMPLATE)
      expect(getTemplateById("deposit")).toBe(DEPOSIT_TEMPLATE)
      expect(getTemplateById("transfer")).toBe(TRANSFER_TEMPLATE)
      expect(getTemplateById("wait")).toBe(WAIT_TEMPLATE)
    })

    it("returns undefined for unknown id", () => {
      expect(getTemplateById("nonexistent")).toBeUndefined()
    })
  })

  describe("TRADE_TEMPLATE", () => {
    it("requires ORDER_SYMBOL, ORDER_AMOUNT, and ORDER_TYPE", () => {
      const required = TRADE_TEMPLATE.params
        .filter((p) => p.required)
        .map((p) => p.key)
      expect(required).toContain("ORDER_SYMBOL")
      expect(required).toContain("ORDER_AMOUNT")
      expect(required).toContain("ORDER_TYPE")
    })

    it("has trading pair detection pattern on ORDER_SYMBOL", () => {
      const symbolParam = TRADE_TEMPLATE.params.find(
        (p) => p.key === "ORDER_SYMBOL",
      )
      expect(symbolParam?.detectPatterns).toBeDefined()
      const patterns = symbolParam!.detectPatterns!
      expect(patterns.some((p) => p.test("BTC/USDT"))).toBe(true)
      expect(patterns.some((p) => p.test("ETH/BTC"))).toBe(true)
      expect(patterns.some((p) => p.test("notapair"))).toBe(false)
    })

    it("marks API_KEY and API_SECRET as sensitive", () => {
      const apiKey = TRADE_TEMPLATE.params.find((p) => p.key === "API_KEY")
      const apiSecret = TRADE_TEMPLATE.params.find(
        (p) => p.key === "API_SECRET",
      )
      expect(apiKey?.sensitive).toBe(true)
      expect(apiSecret?.sensitive).toBe(true)
    })
  })

  describe("TRANSFER_TEMPLATE", () => {
    it("requires blockchain, asset, amount, and destination address", () => {
      const required = TRANSFER_TEMPLATE.params
        .filter((p) => p.required)
        .map((p) => p.key)
      expect(required).toContain("BLOCKCHAIN_FROM")
      expect(required).toContain("BLOCKCHAIN_FROM_ASSET")
      expect(required).toContain("BLOCKCHAIN_FROM_AMOUNT")
      expect(required).toContain("BLOCKCHAIN_TO_ADDRESS")
    })

    it("has EVM address detection on address params", () => {
      const toAddr = TRANSFER_TEMPLATE.params.find(
        (p) => p.key === "BLOCKCHAIN_TO_ADDRESS",
      )
      expect(toAddr?.detectPatterns).toBeDefined()
      const patterns = toAddr!.detectPatterns!
      expect(
        patterns.some((p) =>
          p.test("0x1234567890123456789012345678901234567890"),
        ),
      ).toBe(true)
    })

    it("has BTC address detection on address params", () => {
      const toAddr = TRANSFER_TEMPLATE.params.find(
        (p) => p.key === "BLOCKCHAIN_TO_ADDRESS",
      )
      const patterns = toAddr!.detectPatterns!
      expect(
        patterns.some((p) =>
          p.test("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"),
        ),
      ).toBe(true)
      expect(
        patterns.some((p) => p.test("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")),
      ).toBe(true)
    })

    it("marks private key as sensitive", () => {
      const pk = TRANSFER_TEMPLATE.params.find(
        (p) => p.key === "BLOCKCHAIN_FROM_PRIVATE_KEY",
      )
      expect(pk?.sensitive).toBe(true)
      expect(pk?.type).toBe("password")
    })
  })

  describe("WITHDRAW_TEMPLATE", () => {
    it("requires asset, network, and destination address", () => {
      const required = WITHDRAW_TEMPLATE.params
        .filter((p) => p.required)
        .map((p) => p.key)
      expect(required).toContain("BLOCKCHAIN_TO_ASSET")
      expect(required).toContain("BLOCKCHAIN_TO")
      expect(required).toContain("BLOCKCHAIN_TO_ADDRESS")
    })
  })

  describe("WAIT_TEMPLATE", () => {
    it("requires MIN_DELAY", () => {
      const required = WAIT_TEMPLATE.params
        .filter((p) => p.required)
        .map((p) => p.key)
      expect(required).toContain("MIN_DELAY")
      expect(required).not.toContain("MAX_DELAY")
    })

    it("has numeric detection on delay params", () => {
      const minDelay = WAIT_TEMPLATE.params.find(
        (p) => p.key === "MIN_DELAY",
      )
      const patterns = minDelay!.detectPatterns!
      expect(patterns.some((p) => p.test("10"))).toBe(true)
      expect(patterns.some((p) => p.test("3.5"))).toBe(true)
      expect(patterns.some((p) => p.test("abc"))).toBe(false)
    })
  })

  describe("CANCEL_TEMPLATE", () => {
    it("requires ORDER_SYMBOL", () => {
      const required = CANCEL_TEMPLATE.params
        .filter((p) => p.required)
        .map((p) => p.key)
      expect(required).toContain("ORDER_SYMBOL")
      expect(required).toHaveLength(1)
    })

    it("has order side detection", () => {
      const sideParam = CANCEL_TEMPLATE.params.find(
        (p) => p.key === "ORDER_SIDE",
      )
      expect(sideParam?.detectPatterns).toBeDefined()
      const patterns = sideParam!.detectPatterns!
      expect(patterns.some((p) => p.test("buy"))).toBe(true)
      expect(patterns.some((p) => p.test("sell"))).toBe(true)
    })
  })

  describe("DEPOSIT_TEMPLATE", () => {
    it("requires asset, amount, network, and exchange", () => {
      const required = DEPOSIT_TEMPLATE.params
        .filter((p) => p.required)
        .map((p) => p.key)
      expect(required).toContain("BLOCKCHAIN_FROM_ASSET")
      expect(required).toContain("BLOCKCHAIN_FROM_AMOUNT")
      expect(required).toContain("BLOCKCHAIN_FROM")
      expect(required).toContain("EXCHANGE_TO")
    })

    it("has sensitive params for private key and mnemonic", () => {
      const pk = DEPOSIT_TEMPLATE.params.find(
        (p) => p.key === "BLOCKCHAIN_FROM_PRIVATE_KEY",
      )
      const mnemonic = DEPOSIT_TEMPLATE.params.find(
        (p) => p.key === "BLOCKCHAIN_FROM_MNEMONIC_SEED",
      )
      expect(pk?.sensitive).toBe(true)
      expect(mnemonic?.sensitive).toBe(true)
    })
  })

  describe("regex pattern edge cases", () => {
    it("tradingPair rejects single-char symbols", () => {
      const pattern = TRADE_TEMPLATE.params.find(
        (p) => p.key === "ORDER_SYMBOL",
      )!.detectPatterns![0]
      expect(pattern.test("A/B")).toBe(false)
    })

    it("tradingPair rejects symbols exceeding 10 chars", () => {
      const pattern = TRADE_TEMPLATE.params.find(
        (p) => p.key === "ORDER_SYMBOL",
      )!.detectPatterns![0]
      expect(pattern.test("ABCDEFGHIJK/USDT")).toBe(false)
    })

    it("tradingPair matches case-insensitively", () => {
      const pattern = TRADE_TEMPLATE.params.find(
        (p) => p.key === "ORDER_SYMBOL",
      )!.detectPatterns![0]
      expect(pattern.test("btc/usdt")).toBe(true)
    })

    it("evmAddress rejects wrong-length addresses", () => {
      const pattern = TRANSFER_TEMPLATE.params.find(
        (p) => p.key === "BLOCKCHAIN_TO_ADDRESS",
      )!.detectPatterns![0]
      expect(pattern.test("0x123456789012345678901234567890123456789")).toBe(false) // 39 hex
      expect(pattern.test("0x12345678901234567890123456789012345678901")).toBe(false) // 41 hex
    })

    it("privateKeyHex matches 64-char hex with or without 0x prefix", () => {
      const pk = TRANSFER_TEMPLATE.params.find(
        (p) => p.key === "BLOCKCHAIN_FROM_PRIVATE_KEY",
      )
      const patterns = pk!.detectPatterns!
      const key64 = "a".repeat(64)
      expect(patterns.some((p) => p.test(key64))).toBe(true)
      expect(patterns.some((p) => p.test("0x" + key64))).toBe(true)
      expect(patterns.some((p) => p.test("0x" + "g".repeat(64)))).toBe(false)
    })

    it("mnemonicSeed matches 12 and 24 word phrases", () => {
      const mnemonic = TRANSFER_TEMPLATE.params.find(
        (p) => p.key === "BLOCKCHAIN_FROM_MNEMONIC_SEED",
      )
      const patterns = mnemonic!.detectPatterns!
      const words12 = Array(12).fill("abandon").join(" ")
      const words24 = Array(24).fill("abandon").join(" ")
      expect(patterns.some((p) => p.test(words12))).toBe(true)
      expect(patterns.some((p) => p.test(words24))).toBe(true)
      expect(patterns.some((p) => p.test("only three words"))).toBe(false)
    })
  })

  describe("detection patterns on params", () => {
    it("each param with detectPatterns has valid regexes", () => {
      for (const template of ACTION_TEMPLATES) {
        for (const param of template.params) {
          if (param.detectPatterns) {
            for (const pattern of param.detectPatterns) {
              expect(pattern).toBeInstanceOf(RegExp)
            }
          }
        }
      }
    })

    it("each param with aliasFuzzy has non-empty strings", () => {
      for (const template of ACTION_TEMPLATES) {
        for (const param of template.params) {
          if (param.aliasFuzzy) {
            for (const alias of param.aliasFuzzy) {
              expect(alias.length).toBeGreaterThan(0)
            }
          }
        }
      }
    })
  })
})
