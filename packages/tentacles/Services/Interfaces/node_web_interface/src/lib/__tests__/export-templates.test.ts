import { beforeEach, describe, expect, it, vi } from "vitest"

import {
  deleteUserExportTemplate,
  EXPORT_TEMPLATES,
  FULL_DETAILS_TEMPLATE,
  GENERAL_EXPORT_TEMPLATE,
  getAllExportTemplates,
  getExportTemplateById,
  loadUserExportTemplates,
  saveUserExportTemplate,
  TRADE_EXPORT_TEMPLATE,
  TRANSFER_EXPORT_TEMPLATE,
  validateExportTemplateJson,
} from "../export-templates"

const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value
    },
    removeItem: (key: string) => {
      delete store[key]
    },
    clear: () => {
      store = {}
    },
  }
})()

vi.stubGlobal("localStorage", localStorageMock)

beforeEach(() => {
  localStorageMock.clear()
})

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

    it("includes error status and error message columns", () => {
      const keys = GENERAL_EXPORT_TEMPLATE.columns.map((c) => c.key)
      expect(keys).toContain("error")
      expect(keys).toContain("error_message")
    })

    it("uses meta paths for task-level data", () => {
      const nameCol = GENERAL_EXPORT_TEMPLATE.columns.find(
        (c) => c.key === "name",
      )
      expect(nameCol?.jsonPath).toBe("__task_name__")
    })
  })

  describe("TRADE_EXPORT_TEMPLATE", () => {
    it("has trade-specific columns from exchange account state", () => {
      const keys = TRADE_EXPORT_TEMPLATE.columns.map((c) => c.key)
      expect(keys).toContain("symbol")
      expect(keys).toContain("side")
      expect(keys).toContain("amount")
      expect(keys).toContain("price")
      expect(keys).toContain("exchange_trade_id")
      expect(keys).toContain("trade_status")
      expect(keys).toContain("error")
      expect(keys).toContain("error_message")
      const prefix = "state.automation.exchange_account_elements.trades[0]"
      const amountCol = TRADE_EXPORT_TEMPLATE.columns.find(
        (c) => c.key === "amount",
      )
      expect(amountCol?.jsonPath).toBe(`${prefix}.amount`)
    })

    it("uses number formatter for amount, price, and cost", () => {
      const amountCol = TRADE_EXPORT_TEMPLATE.columns.find(
        (c) => c.key === "amount",
      )
      const priceCol = TRADE_EXPORT_TEMPLATE.columns.find(
        (c) => c.key === "price",
      )
      const costCol = TRADE_EXPORT_TEMPLATE.columns.find(
        (c) => c.key === "cost",
      )
      expect(amountCol?.formatter).toBe("number")
      expect(priceCol?.formatter).toBe("number")
      expect(costCol?.formatter).toBe("number")
    })
  })

  describe("TRANSFER_EXPORT_TEMPLATE", () => {
    it("has address and transaction columns", () => {
      const keys = TRANSFER_EXPORT_TEMPLATE.columns.map((c) => c.key)
      expect(keys).toContain("address_from")
      expect(keys).toContain("address_to")
      expect(keys).toContain("txid")
      expect(keys).toContain("error")
      expect(keys).toContain("error_message")
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

  describe("getExportTemplateById", () => {
    it("finds user-imported templates", () => {
      saveUserExportTemplate({
        id: "user_findable",
        label: "User Findable",
        description: "",
        columns: [],
      })
      expect(getExportTemplateById("user_findable")).toBeDefined()
    })
  })
})

// ── validateExportTemplateJson ─────────────────────────────────────────

describe("validateExportTemplateJson", () => {
  it("accepts a valid export template", () => {
    const valid = {
      id: "my_template",
      label: "My Template",
      description: "A description",
      columns: [
        {
          key: "name",
          label: "Name",
          jsonPath: "__task_name__",
          formatter: "text",
        },
      ],
    }
    expect(() => validateExportTemplateJson(valid)).not.toThrow()
    const result = validateExportTemplateJson(valid)
    expect(result.id).toBe("my_template")
  })

  it("accepts empty columns array", () => {
    const valid = { id: "x", label: "X", description: "", columns: [] }
    expect(() => validateExportTemplateJson(valid)).not.toThrow()
  })

  it("accepts columns without optional formatter", () => {
    const valid = {
      id: "x",
      label: "X",
      description: "",
      columns: [{ key: "k", label: "L", jsonPath: "path" }],
    }
    expect(() => validateExportTemplateJson(valid)).not.toThrow()
  })

  it("rejects missing required fields", () => {
    expect(() => validateExportTemplateJson({ id: "x", label: "X" })).toThrow()
    expect(() => validateExportTemplateJson({})).toThrow()
    expect(() => validateExportTemplateJson(null)).toThrow()
  })

  it("rejects empty string id", () => {
    const invalid = { id: "", label: "X", description: "", columns: [] }
    expect(() => validateExportTemplateJson(invalid)).toThrow()
  })

  it("rejects column with empty key", () => {
    const invalid = {
      id: "x",
      label: "X",
      description: "",
      columns: [{ key: "", label: "L", jsonPath: "path" }],
    }
    expect(() => validateExportTemplateJson(invalid)).toThrow()
  })

  it("rejects invalid formatter value", () => {
    const invalid = {
      id: "x",
      label: "X",
      description: "",
      columns: [
        { key: "k", label: "L", jsonPath: "path", formatter: "invalid" },
      ],
    }
    expect(() => validateExportTemplateJson(invalid)).toThrow()
  })
})

// ── localStorage CRUD ──────────────────────────────────────────────────

describe("loadUserExportTemplates", () => {
  it("returns empty array when nothing is stored", () => {
    expect(loadUserExportTemplates()).toEqual([])
  })

  it("returns stored templates", () => {
    localStorage.setItem(
      "user_export_templates",
      JSON.stringify([
        { id: "stored", label: "Stored", description: "", columns: [] },
      ]),
    )
    expect(loadUserExportTemplates()).toHaveLength(1)
    expect(loadUserExportTemplates()[0].id).toBe("stored")
  })

  it("silently ignores malformed entries", () => {
    localStorage.setItem(
      "user_export_templates",
      JSON.stringify([
        { id: "valid", label: "V", description: "", columns: [] },
        { broken: true },
      ]),
    )
    expect(loadUserExportTemplates()).toHaveLength(1)
  })
})

describe("saveUserExportTemplate", () => {
  it("saves a new template", () => {
    saveUserExportTemplate({
      id: "my_custom",
      label: "My Custom",
      description: "",
      columns: [],
    })
    expect(loadUserExportTemplates()).toHaveLength(1)
  })

  it("replaces an existing template with the same id", () => {
    saveUserExportTemplate({
      id: "replaceable",
      label: "Original",
      description: "",
      columns: [],
    })
    saveUserExportTemplate({
      id: "replaceable",
      label: "Updated",
      description: "",
      columns: [],
    })
    const templates = loadUserExportTemplates()
    expect(templates).toHaveLength(1)
    expect(templates[0].label).toBe("Updated")
  })

  it("throws when id collides with a built-in template", () => {
    expect(() =>
      saveUserExportTemplate({
        id: "general",
        label: "Collision",
        description: "",
        columns: [],
      }),
    ).toThrow(/reserved/)
    expect(() =>
      saveUserExportTemplate({
        id: "trade",
        label: "Collision",
        description: "",
        columns: [],
      }),
    ).toThrow(/reserved/)
  })
})

describe("deleteUserExportTemplate", () => {
  it("removes the template with the given id", () => {
    saveUserExportTemplate({
      id: "to_delete",
      label: "To Delete",
      description: "",
      columns: [],
    })
    deleteUserExportTemplate("to_delete")
    expect(loadUserExportTemplates()).toHaveLength(0)
  })

  it("is a no-op for a non-existent id", () => {
    expect(() => deleteUserExportTemplate("nonexistent")).not.toThrow()
  })
})

describe("getAllExportTemplates", () => {
  it("includes built-in templates", () => {
    const ids = getAllExportTemplates().map((t) => t.id)
    expect(ids).toContain("general")
    expect(ids).toContain("trade")
    expect(ids).toContain("transfer")
    expect(ids).toContain("full")
  })

  it("includes user-imported templates", () => {
    saveUserExportTemplate({
      id: "user_template",
      label: "User",
      description: "",
      columns: [],
    })
    const ids = getAllExportTemplates().map((t) => t.id)
    expect(ids).toContain("user_template")
  })

  it("skips malformed user templates", () => {
    localStorage.setItem(
      "user_export_templates",
      JSON.stringify([{ broken: true }]),
    )
    const ids = getAllExportTemplates().map((t) => t.id)
    expect(ids).toContain("general")
    expect(ids).toHaveLength(4) // only built-ins
  })
})
