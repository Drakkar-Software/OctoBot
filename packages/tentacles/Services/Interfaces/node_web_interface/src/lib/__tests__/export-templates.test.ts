import { describe, expect, it } from "vitest"

import {
  EXPORT_TEMPLATES,
  getExportTemplateById,
  GENERAL_EXPORT_TEMPLATE,
  TRADE_EXPORT_TEMPLATE,
  TRANSFER_EXPORT_TEMPLATE,
  FULL_DETAILS_TEMPLATE,
} from "../export-templates"

describe("export-templates", () => {
  describe("template registry", () => {
    it("contains all 4 templates", () => {
      expect(EXPORT_TEMPLATES).toHaveLength(4)
    })

    it("each template has a unique id", () => {
      const ids = EXPORT_TEMPLATES.map((t) => t.id)
      expect(new Set(ids).size).toBe(ids.length)
    })

    it("each template has required fields", () => {
      for (const template of EXPORT_TEMPLATES) {
        expect(template.id).toBeTruthy()
        expect(template.label).toBeTruthy()
        expect(template.description).toBeTruthy()
      }
    })
  })

  describe("getExportTemplateById", () => {
    it("returns correct template", () => {
      expect(getExportTemplateById("general")).toBe(GENERAL_EXPORT_TEMPLATE)
      expect(getExportTemplateById("trade")).toBe(TRADE_EXPORT_TEMPLATE)
      expect(getExportTemplateById("transfer")).toBe(TRANSFER_EXPORT_TEMPLATE)
      expect(getExportTemplateById("full")).toBe(FULL_DETAILS_TEMPLATE)
    })

    it("returns undefined for unknown id", () => {
      expect(getExportTemplateById("unknown")).toBeUndefined()
    })
  })

  describe("GENERAL_EXPORT_TEMPLATE", () => {
    it("has name, status, and date columns", () => {
      const keys = GENERAL_EXPORT_TEMPLATE.columns.map((c) => c.key)
      expect(keys).toContain("name")
      expect(keys).toContain("status")
      expect(keys).toContain("completed_at")
    })

    it("uses meta paths for task-level data", () => {
      const nameCol = GENERAL_EXPORT_TEMPLATE.columns.find(
        (c) => c.key === "name",
      )
      expect(nameCol?.jsonPath).toBe("__task_name__")
    })
  })

  describe("TRADE_EXPORT_TEMPLATE", () => {
    it("has trade-specific columns", () => {
      const keys = TRADE_EXPORT_TEMPLATE.columns.map((c) => c.key)
      expect(keys).toContain("symbol")
      expect(keys).toContain("side")
      expect(keys).toContain("amount")
      expect(keys).toContain("price")
      expect(keys).toContain("exchange")
    })

    it("uses number formatter for amount and price", () => {
      const amountCol = TRADE_EXPORT_TEMPLATE.columns.find(
        (c) => c.key === "amount",
      )
      const priceCol = TRADE_EXPORT_TEMPLATE.columns.find(
        (c) => c.key === "price",
      )
      expect(amountCol?.formatter).toBe("number")
      expect(priceCol?.formatter).toBe("number")
    })
  })

  describe("TRANSFER_EXPORT_TEMPLATE", () => {
    it("has address and tx_hash columns", () => {
      const keys = TRANSFER_EXPORT_TEMPLATE.columns.map((c) => c.key)
      expect(keys).toContain("from_address")
      expect(keys).toContain("to_address")
      expect(keys).toContain("tx_hash")
    })
  })

  describe("FULL_DETAILS_TEMPLATE", () => {
    it("has empty columns (populated dynamically)", () => {
      expect(FULL_DETAILS_TEMPLATE.columns).toHaveLength(0)
    })
  })

  describe("column definitions", () => {
    it("all columns have key, label, and jsonPath", () => {
      for (const template of EXPORT_TEMPLATES) {
        for (const col of template.columns) {
          expect(col.key).toBeTruthy()
          expect(col.label).toBeTruthy()
          expect(col.jsonPath).toBeTruthy()
        }
      }
    })
  })
})
