import { beforeEach, describe, expect, it, vi } from "vitest"

import {
  deleteUserMetaTemplate,
  getAllTemplates,
  getTemplateById,
  loadUserMetaTemplates,
  resolveMetaTemplate,
  saveUserMetaTemplate,
  validateMetaTemplateJson,
  type MetaTemplateDef,
} from "../meta-templates"

const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
  }
})()

vi.stubGlobal("localStorage", localStorageMock)

beforeEach(() => {
  localStorageMock.clear()
})

// ── resolveMetaTemplate ────────────────────────────────────────────────

describe("resolveMetaTemplate", () => {
  it("merges params from all steps in order", () => {
    const def: MetaTemplateDef = {
      id: "test",
      label: "Test",
      description: "Test meta template",
      steps: [{ templateId: "wait" }, { templateId: "cancel" }],
    }
    const resolved = resolveMetaTemplate(def)
    const keys = resolved.params.map((p) => p.key)
    // wait params come first
    expect(keys[0]).toBe("MIN_DELAY")
    // cancel params follow
    expect(keys).toContain("ORDER_SYMBOL")
  })

  it("concatenates actionTypes from all steps", () => {
    const def: MetaTemplateDef = {
      id: "test",
      label: "Test",
      description: "",
      steps: [{ templateId: "wait" }, { templateId: "trade" }],
    }
    const resolved = resolveMetaTemplate(def)
    expect(resolved.actionTypes).toEqual(["wait", "trade"])
  })

  it("deduplicates actionTypes", () => {
    const def: MetaTemplateDef = {
      id: "test",
      label: "Test",
      description: "",
      steps: [{ templateId: "trade" }, { templateId: "trade" }],
    }
    const resolved = resolveMetaTemplate(def)
    expect(resolved.actionTypes).toEqual(["trade"])
  })

  it("applies first-occurrence-wins for duplicate param keys", () => {
    // Both wait and... let's use two copies of wait — MIN_DELAY should appear only once
    const def: MetaTemplateDef = {
      id: "test",
      label: "Test",
      description: "",
      steps: [{ templateId: "wait" }, { templateId: "wait" }],
    }
    const resolved = resolveMetaTemplate(def)
    const delayParams = resolved.params.filter((p) => p.key === "MIN_DELAY")
    expect(delayParams).toHaveLength(1)
  })

  it("applies override as defaultValue on the matching param", () => {
    const def: MetaTemplateDef = {
      id: "test",
      label: "Test",
      description: "",
      steps: [{ templateId: "trade", overrides: { EXCHANGE_TO: "kraken" } }],
    }
    const resolved = resolveMetaTemplate(def)
    const exchangeParam = resolved.params.find((p) => p.key === "EXCHANGE_TO")
    expect(exchangeParam?.defaultValue).toBe("kraken")
  })

  it("sets hidden:true on hiddenParams", () => {
    const def: MetaTemplateDef = {
      id: "test",
      label: "Test",
      description: "",
      steps: [{ templateId: "trade", hiddenParams: ["API_KEY", "API_SECRET"] }],
    }
    const resolved = resolveMetaTemplate(def)
    const apiKey = resolved.params.find((p) => p.key === "API_KEY")
    const apiSecret = resolved.params.find((p) => p.key === "API_SECRET")
    expect(apiKey?.hidden).toBe(true)
    expect(apiSecret?.hidden).toBe(true)
  })

  it("throws on hidden+required param without default or override", () => {
    const def: MetaTemplateDef = {
      id: "test",
      label: "Test",
      description: "",
      steps: [{ templateId: "trade", hiddenParams: ["ORDER_SYMBOL"] }],
    }
    expect(() => resolveMetaTemplate(def)).toThrow()
  })

  it("does not throw on hidden+required param with override", () => {
    const def: MetaTemplateDef = {
      id: "test",
      label: "Test",
      description: "",
      steps: [{
        templateId: "trade",
        hiddenParams: ["ORDER_SYMBOL"],
        overrides: { ORDER_SYMBOL: "BTC/USDT" },
      }],
    }
    expect(() => resolveMetaTemplate(def)).not.toThrow()
    const resolved = resolveMetaTemplate(def)
    const sym = resolved.params.find((p) => p.key === "ORDER_SYMBOL")
    expect(sym?.hidden).toBe(true)
    expect(sym?.defaultValue).toBe("BTC/USDT")
  })

  it("throws when a step references an unknown base template", () => {
    const def: MetaTemplateDef = {
      id: "test",
      label: "Test",
      description: "",
      steps: [{ templateId: "nonexistent" }],
    }
    expect(() => resolveMetaTemplate(def)).toThrow(/nonexistent/)
  })

  it("preserves template id, label, and description from the def", () => {
    const def: MetaTemplateDef = {
      id: "my_meta",
      label: "My Meta",
      description: "A test",
      steps: [{ templateId: "wait" }],
    }
    const resolved = resolveMetaTemplate(def)
    expect(resolved.id).toBe("my_meta")
    expect(resolved.label).toBe("My Meta")
    expect(resolved.description).toBe("A test")
  })
})

describe("validateMetaTemplateJson", () => {
  it("accepts a valid MetaTemplateDef", () => {
    const valid = {
      id: "my_template",
      label: "My Template",
      description: "A description",
      steps: [{ templateId: "wait" }],
    }
    expect(() => validateMetaTemplateJson(valid)).not.toThrow()
    const result = validateMetaTemplateJson(valid)
    expect(result.id).toBe("my_template")
  })

  it("accepts optional overrides and hiddenParams", () => {
    const valid = {
      id: "t",
      label: "T",
      description: "",
      steps: [{
        templateId: "trade",
        overrides: { EXCHANGE_TO: "binance" },
        hiddenParams: ["API_KEY"],
      }],
    }
    expect(() => validateMetaTemplateJson(valid)).not.toThrow()
  })

  it("rejects missing required fields", () => {
    expect(() => validateMetaTemplateJson({ id: "x", label: "X" })).toThrow()
    expect(() => validateMetaTemplateJson({})).toThrow()
    expect(() => validateMetaTemplateJson(null)).toThrow()
  })

  it("rejects empty steps array", () => {
    const invalid = { id: "t", label: "T", description: "", steps: [] }
    expect(() => validateMetaTemplateJson(invalid)).toThrow()
  })

  it("rejects empty string id", () => {
    const invalid = {
      id: "",
      label: "T",
      description: "",
      steps: [{ templateId: "wait" }],
    }
    expect(() => validateMetaTemplateJson(invalid)).toThrow()
  })
})

// ── localStorage CRUD ──────────────────────────────────────────────────

describe("loadUserMetaTemplates", () => {
  it("returns empty array when nothing is stored", () => {
    expect(loadUserMetaTemplates()).toEqual([])
  })

  it("returns stored templates", () => {
    const def: MetaTemplateDef = {
      id: "user_test",
      label: "User Test",
      description: "",
      steps: [{ templateId: "wait" }],
    }
    localStorage.setItem("user_meta_templates", JSON.stringify([def]))
    expect(loadUserMetaTemplates()).toHaveLength(1)
    expect(loadUserMetaTemplates()[0].id).toBe("user_test")
  })

  it("silently ignores malformed entries", () => {
    localStorage.setItem("user_meta_templates", JSON.stringify([
      { id: "valid", label: "V", description: "", steps: [{ templateId: "wait" }] },
      { broken: true },
    ]))
    expect(loadUserMetaTemplates()).toHaveLength(1)
  })
})

describe("saveUserMetaTemplate", () => {
  it("saves a new template", () => {
    const def: MetaTemplateDef = {
      id: "my_custom",
      label: "My Custom",
      description: "",
      steps: [{ templateId: "wait" }],
    }
    saveUserMetaTemplate(def)
    expect(loadUserMetaTemplates()).toHaveLength(1)
  })

  it("replaces an existing template with the same id", () => {
    const def: MetaTemplateDef = {
      id: "replaceable",
      label: "Original",
      description: "",
      steps: [{ templateId: "wait" }],
    }
    saveUserMetaTemplate(def)
    saveUserMetaTemplate({ ...def, label: "Updated" })
    const templates = loadUserMetaTemplates()
    expect(templates).toHaveLength(1)
    expect(templates[0].label).toBe("Updated")
  })

  it("throws when id collides with a base template", () => {
    const def: MetaTemplateDef = {
      id: "trade",
      label: "Collision",
      description: "",
      steps: [{ templateId: "wait" }],
    }
    expect(() => saveUserMetaTemplate(def)).toThrow(/reserved/)
  })

})

describe("deleteUserMetaTemplate", () => {
  it("removes the template with the given id", () => {
    const def: MetaTemplateDef = {
      id: "to_delete",
      label: "To Delete",
      description: "",
      steps: [{ templateId: "wait" }],
    }
    saveUserMetaTemplate(def)
    deleteUserMetaTemplate("to_delete")
    expect(loadUserMetaTemplates()).toHaveLength(0)
  })

  it("is a no-op for a non-existent id", () => {
    expect(() => deleteUserMetaTemplate("nonexistent")).not.toThrow()
  })
})

describe("getAllTemplates", () => {
  it("includes base templates", () => {
    const ids = getAllTemplates().map((t) => t.id)
    expect(ids).toContain("trade")
    expect(ids).toContain("wait")
    expect(ids).toContain("transfer")
  })

  it("includes user-imported templates", () => {
    const def: MetaTemplateDef = {
      id: "user_template",
      label: "User",
      description: "",
      steps: [{ templateId: "wait" }],
    }
    saveUserMetaTemplate(def)
    const ids = getAllTemplates().map((t) => t.id)
    expect(ids).toContain("user_template")
  })

  it("skips user templates that fail to resolve", () => {
    // Inject a template referencing a nonexistent base
    localStorage.setItem("user_meta_templates", JSON.stringify([
      { id: "broken_user", label: "Broken", description: "", steps: [{ templateId: "nonexistent" }] },
    ]))
    const ids = getAllTemplates().map((t) => t.id)
    expect(ids).not.toContain("broken_user")
  })
})

describe("getTemplateById", () => {
  it("finds base templates", () => {
    expect(getTemplateById("trade")).toBeDefined()
    expect(getTemplateById("cancel")).toBeDefined()
  })

  it("finds user-imported templates", () => {
    const def: MetaTemplateDef = {
      id: "findable_user",
      label: "Findable",
      description: "",
      steps: [{ templateId: "wait" }],
    }
    saveUserMetaTemplate(def)
    expect(getTemplateById("findable_user")).toBeDefined()
  })

  it("returns undefined for unknown id", () => {
    expect(getTemplateById("nonexistent")).toBeUndefined()
  })
})
