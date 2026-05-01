import { describe, expect, it } from "vitest"

import { escapeCSVValue } from "../csv"
import { extractValue, flattenJSON } from "../json-path"

describe("security", () => {
  describe("CSV formula injection prevention", () => {
    it("prefixes values starting with = to prevent formula injection", () => {
      const result = escapeCSVValue("=SUM(A1:A10)")
      expect(result).toBe('"\'=SUM(A1:A10)"')
    })

    it("prefixes values starting with + to prevent formula injection", () => {
      const result = escapeCSVValue("+cmd|' /C calc'!A0")
      expect(result).toBe("\"'+cmd|' /C calc'!A0\"")
    })

    it("prefixes values starting with - to prevent formula injection", () => {
      const result = escapeCSVValue("-1+1")
      expect(result).toBe('"\'-1+1"')
    })

    it("prefixes values starting with @ to prevent formula injection", () => {
      const result = escapeCSVValue("@SUM(A1)")
      expect(result).toBe('"\'@SUM(A1)"')
    })

    it("prefixes values starting with tab to prevent formula injection", () => {
      const result = escapeCSVValue("\tcmd")
      expect(result).toBe('"\'\tcmd"')
    })

    it("prefixes values starting with carriage return to prevent formula injection", () => {
      const result = escapeCSVValue("\rcmd")
      expect(result).toBe('"\'\rcmd"')
    })

    it("does not prefix normal values", () => {
      expect(escapeCSVValue("hello")).toBe("hello")
      expect(escapeCSVValue("123")).toBe("123")
      expect(escapeCSVValue("0x1234")).toBe("0x1234")
    })

    it("handles null and undefined values", () => {
      expect(escapeCSVValue(null)).toBe("")
      expect(escapeCSVValue(undefined)).toBe("")
    })

    it("converts objects to JSON strings", () => {
      const result = escapeCSVValue({ key: "value" })
      expect(result).toContain("key")
      expect(result).toContain("value")
    })

    it("escapes values with both formula chars and quotes", () => {
      const result = escapeCSVValue('=SUM("A1")')
      expect(result).toBe('"\'=SUM(""A1"")"')
    })
  })

  describe("prototype pollution prevention in extractValue", () => {
    it("blocks __proto__ traversal", () => {
      const obj = { __proto__: { polluted: true } }
      expect(extractValue(obj, "__proto__.polluted")).toBeUndefined()
    })

    it("blocks constructor traversal", () => {
      const obj = { constructor: { prototype: { polluted: true } } }
      expect(
        extractValue(obj, "constructor.prototype.polluted"),
      ).toBeUndefined()
    })

    it("blocks prototype traversal", () => {
      const obj = { prototype: { polluted: true } }
      expect(extractValue(obj, "prototype.polluted")).toBeUndefined()
    })

    it("allows normal keys that contain dangerous substrings", () => {
      const obj = { my_constructor_value: 42 }
      expect(extractValue(obj, "my_constructor_value")).toBe(42)
    })
  })

  describe("prototype pollution prevention in flattenJSON", () => {
    it("skips __proto__ keys when flattening", () => {
      // JSON.parse can create objects with __proto__ keys
      const obj = JSON.parse('{"__proto__": {"polluted": true}, "safe": 1}')
      const result = flattenJSON(obj)
      expect(result.safe).toBe(1)
      expect(result["__proto__.polluted"]).toBeUndefined()
    })

    it("skips constructor keys when flattening", () => {
      const obj = { constructor: { prototype: { x: 1 } }, data: "ok" }
      const result = flattenJSON(obj)
      expect(result.data).toBe("ok")
      expect(result["constructor.prototype.x"]).toBeUndefined()
    })
  })
})
