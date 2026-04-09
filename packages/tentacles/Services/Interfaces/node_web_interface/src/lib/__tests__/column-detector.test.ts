import { describe, expect, it } from "vitest"

import {
  detectColumnsAndTemplates,
  detectMappingsForTemplate,
  buildParamValuesForRow,
  extractColumnValues,
} from "../column-detector"
import { TRANSFER_TEMPLATE, TRADE_TEMPLATE, WAIT_TEMPLATE } from "../action-templates"

describe("column-detector", () => {
  describe("extractColumnValues", () => {
    it("transposes rows into column arrays", () => {
      const headers = ["a", "b", "c"]
      const rows = [
        ["1", "2", "3"],
        ["4", "5", "6"],
      ]
      const result = extractColumnValues(headers, rows)
      expect(result).toEqual([
        ["1", "4"],
        ["2", "5"],
        ["3", "6"],
      ])
    })

    it("handles missing values in rows", () => {
      const headers = ["a", "b"]
      const rows = [["1"], ["4", "5"]]
      const result = extractColumnValues(headers, rows)
      expect(result[0]).toEqual(["1", "4"])
      expect(result[1]).toEqual(["", "5"])
    })
  })

  describe("detectColumnsAndTemplates", () => {
    it("detects transfer template from EVM addresses and amounts", () => {
      const headers = ["destination", "amount", "asset", "network", "from_addr"]
      const rows = [
        [
          "0x1234567890123456789012345678901234567890",
          "1.5",
          "ETH",
          "ethereum",
          "0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
        ],
      ]

      const results = detectColumnsAndTemplates(headers, rows)
      expect(results).toHaveLength(1)
      expect(results[0].templateId).toBe("transfer")
    })

    it("detects trade template from trading pairs and order types", () => {
      const headers = ["symbol", "order_amount", "order_type", "side", "exchange"]
      const rows = [["BTC/USDT", "0.5", "market", "buy", "binance"]]

      const results = detectColumnsAndTemplates(headers, rows)
      expect(results).toHaveLength(1)
      expect(results[0].templateId).toBe("trade")
    })

    it("maps values correctly for transfer with BTC addresses", () => {
      const headers = ["to_address", "amount", "coin", "chain"]
      const rows = [
        [
          "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
          "0.01",
          "BTC",
          "bitcoin",
        ],
      ]

      const results = detectColumnsAndTemplates(headers, rows)
      expect(results).toHaveLength(1)
      const result = results[0]

      // Should have mapped the BTC address to an address param
      const addressMapping = result.mappings.find((m) =>
        m.paramKey.includes("ADDRESS"),
      )
      expect(addressMapping).toBeDefined()
      expect(
        result.paramValues[addressMapping!.paramKey],
      ).toBe("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4")
    })

    it("handles multiple rows, all get the same detected template", () => {
      const headers = ["address", "amount"]
      const rows = [
        ["0x1234567890123456789012345678901234567890", "1.0"],
        ["0xABCDEF1234567890ABCDEF1234567890ABCDEF12", "2.0"],
      ]

      const results = detectColumnsAndTemplates(headers, rows)
      expect(results).toHaveLength(2)
      expect(results[0].templateId).toBe(results[1].templateId)
    })

    it("returns unmapped columns for columns that don't match any param", () => {
      const headers = ["address", "amount", "zzzfoo", "xxxbar", "yyyqux"]
      const rows = [
        [
          "0x1234567890123456789012345678901234567890",
          "1.0",
          "some notes",
          "extra",
          "more",
        ],
      ]

      const results = detectColumnsAndTemplates(headers, rows)
      // At least some columns should be unmapped since "zzzfoo", "xxxbar", "yyyqux"
      // don't match any known patterns or aliases
      expect(results[0].unmappedColumns.length).toBeGreaterThan(0)
    })

    it("handles empty rows gracefully", () => {
      const headers = ["a", "b"]
      const rows: string[][] = []

      const results = detectColumnsAndTemplates(headers, rows)
      expect(results).toHaveLength(0)
    })

    it("falls back gracefully when no columns match any template", () => {
      const headers = ["color", "shape"]
      const rows = [["red", "circle"]]

      const results = detectColumnsAndTemplates(headers, rows)
      expect(results).toHaveLength(1)
      // Should still return a result with some template (even if low score)
      expect(results[0].templateId).toBeTruthy()
    })

    it("handles headers with special characters via normalization", () => {
      const headers = ["to-address", "FROM_AMOUNT", "blockchain_network"]
      const rows = [
        ["0x1234567890123456789012345678901234567890", "1.5", "ethereum"],
      ]

      const results = detectColumnsAndTemplates(headers, rows)
      expect(results).toHaveLength(1)
      // Should map despite dashes/underscores
      expect(Object.keys(results[0].paramValues).length).toBeGreaterThan(0)
    })

    it("detects wait template from delay-related headers", () => {
      const headers = ["delay", "max_delay"]
      const rows = [["10", "30"]]

      const results = detectColumnsAndTemplates(headers, rows)
      expect(results).toHaveLength(1)
      expect(results[0].templateId).toBe("wait")
    })
  })

  describe("detectMappingsForTemplate", () => {
    it("maps columns to transfer template params", () => {
      const headers = ["to_addr", "amount", "token", "blockchain"]
      const rows = [
        [
          "0x1234567890123456789012345678901234567890",
          "1.0",
          "ETH",
          "ethereum",
        ],
      ]

      const mappings = detectMappingsForTemplate(
        TRANSFER_TEMPLATE,
        headers,
        rows,
      )
      expect(mappings.length).toBeGreaterThan(0)

      // Check that address column was matched
      const addrMapping = mappings.find((m) =>
        m.paramKey.includes("ADDRESS"),
      )
      expect(addrMapping).toBeDefined()
      expect(addrMapping!.columnIndex).toBe(0) // "to_addr"
    })

    it("maps columns to trade template params", () => {
      const headers = ["pair", "qty", "type", "exchange"]
      const rows = [["BTC/USDT", "0.1", "limit", "binance"]]

      const mappings = detectMappingsForTemplate(
        TRADE_TEMPLATE,
        headers,
        rows,
      )

      const symbolMapping = mappings.find(
        (m) => m.paramKey === "ORDER_SYMBOL",
      )
      expect(symbolMapping).toBeDefined()
    })

    it("assigns confidence levels", () => {
      const headers = ["address", "amount"]
      const rows = [
        ["0x1234567890123456789012345678901234567890", "1.0"],
      ]

      const mappings = detectMappingsForTemplate(
        TRANSFER_TEMPLATE,
        headers,
        rows,
      )

      // Address has both value pattern + fuzzy header match => high confidence
      const addrMapping = mappings.find((m) =>
        m.paramKey.includes("ADDRESS"),
      )
      expect(addrMapping?.confidence).toBe("high")
    })
  })

  describe("buildParamValuesForRow", () => {
    it("extracts values from row based on mappings", () => {
      const row = ["0x1234567890123456789012345678901234567890", "1.5", "ETH"]
      const mappings = [
        { columnIndex: 0, paramKey: "BLOCKCHAIN_TO_ADDRESS", confidence: "high" as const },
        { columnIndex: 1, paramKey: "BLOCKCHAIN_FROM_AMOUNT", confidence: "medium" as const },
        { columnIndex: 2, paramKey: "BLOCKCHAIN_FROM_ASSET", confidence: "low" as const },
      ]

      const values = buildParamValuesForRow(row, mappings)
      expect(values.BLOCKCHAIN_TO_ADDRESS).toBe(
        "0x1234567890123456789012345678901234567890",
      )
      expect(values.BLOCKCHAIN_FROM_AMOUNT).toBe("1.5")
      expect(values.BLOCKCHAIN_FROM_ASSET).toBe("ETH")
    })

    it("skips empty values", () => {
      const row = ["", "1.5"]
      const mappings = [
        { columnIndex: 0, paramKey: "ADDRESS", confidence: "high" as const },
        { columnIndex: 1, paramKey: "AMOUNT", confidence: "medium" as const },
      ]

      const values = buildParamValuesForRow(row, mappings)
      expect(values.ADDRESS).toBeUndefined()
      expect(values.AMOUNT).toBe("1.5")
    })

    it("handles out-of-bounds column index gracefully", () => {
      const row = ["a", "b"]
      const mappings = [
        { columnIndex: 10, paramKey: "MISSING", confidence: "high" as const },
      ]

      const values = buildParamValuesForRow(row, mappings)
      expect(values.MISSING).toBeUndefined()
    })

    it("trims whitespace-only values", () => {
      const row = ["  ", "1.5"]
      const mappings = [
        { columnIndex: 0, paramKey: "ADDR", confidence: "high" as const },
        { columnIndex: 1, paramKey: "AMT", confidence: "medium" as const },
      ]

      const values = buildParamValuesForRow(row, mappings)
      expect(values.ADDR).toBeUndefined()
      expect(values.AMT).toBe("1.5")
    })
  })
})
