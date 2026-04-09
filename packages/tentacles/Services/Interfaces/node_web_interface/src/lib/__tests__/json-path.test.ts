import { describe, expect, it } from "vitest"

import {
  extractValue,
  flattenJSON,
  discoverPaths,
  formatCellValue,
} from "../json-path"

describe("json-path", () => {
  describe("extractValue", () => {
    it("extracts top-level keys", () => {
      expect(extractValue({ name: "test" }, "name")).toBe("test")
    })

    it("extracts nested keys with dot notation", () => {
      const obj = { a: { b: { c: 42 } } }
      expect(extractValue(obj, "a.b.c")).toBe(42)
    })

    it("extracts array elements with bracket notation", () => {
      const obj = { items: ["first", "second", "third"] }
      expect(extractValue(obj, "items[1]")).toBe("second")
    })

    it("extracts nested objects inside arrays", () => {
      const obj = { orders: [{ id: 1 }, { id: 2 }] }
      expect(extractValue(obj, "orders[0].id")).toBe(1)
    })

    it("returns undefined for missing paths", () => {
      expect(extractValue({ a: 1 }, "b")).toBeUndefined()
      expect(extractValue({ a: 1 }, "a.b.c")).toBeUndefined()
    })

    it("returns undefined for null/undefined input", () => {
      expect(extractValue(null, "a")).toBeUndefined()
      expect(extractValue(undefined, "a")).toBeUndefined()
    })

    it("extracts nested array elements", () => {
      const obj = { items: [[1, 2], [3, 4]] }
      expect(extractValue(obj, "items[0][1]")).toBe(2)
      expect(extractValue(obj, "items[1][0]")).toBe(3)
    })

    it("preserves boolean values", () => {
      expect(extractValue({ a: false }, "a")).toBe(false)
      expect(extractValue({ a: true }, "a")).toBe(true)
    })

    it("handles numeric keys on objects", () => {
      expect(extractValue({ "0": "zero" }, "0")).toBe("zero")
    })

    it("returns undefined for path through primitive", () => {
      expect(extractValue({ a: "string" }, "a.b")).toBeUndefined()
    })
  })

  describe("flattenJSON", () => {
    it("flattens simple object", () => {
      const result = flattenJSON({ a: 1, b: "hello" })
      expect(result).toEqual({ a: 1, b: "hello" })
    })

    it("flattens nested object with dot notation", () => {
      const result = flattenJSON({ a: { b: { c: 42 } } })
      expect(result).toEqual({ "a.b.c": 42 })
    })

    it("flattens arrays with bracket notation", () => {
      const result = flattenJSON({ items: [1, 2, 3] })
      expect(result).toEqual({
        "items[0]": 1,
        "items[1]": 2,
        "items[2]": 3,
      })
    })

    it("handles empty objects and arrays", () => {
      const result = flattenJSON({ a: {}, b: [] })
      expect(result).toEqual({ a: {}, b: [] })
    })

    it("handles null values", () => {
      const result = flattenJSON({ a: null })
      expect(result).toEqual({ a: null })
    })

    it("respects maxDepth by stopping recursion", () => {
      const deep = { a: { b: { c: { d: "deep" } } } }
      const result = flattenJSON(deep, "", 2)
      // Depth: 0=root, 1=a, 2=b, 3=c exceeds maxDepth → "a.b.c" stores remaining
      expect(result["a.b.c"]).toEqual({ d: "deep" })
      expect(result["a.b.c.d"]).toBeUndefined()
    })

    it("flattens nested arrays", () => {
      const result = flattenJSON({ a: [[1, 2], [3]] })
      expect(result["a[0][0]"]).toBe(1)
      expect(result["a[0][1]"]).toBe(2)
      expect(result["a[1][0]"]).toBe(3)
    })

    it("flattens mixed nested structures", () => {
      const result = flattenJSON({ a: [{ b: [1, 2] }] })
      expect(result["a[0].b[0]"]).toBe(1)
      expect(result["a[0].b[1]"]).toBe(2)
    })

    it("preserves boolean and numeric leaf values", () => {
      const result = flattenJSON({ flag: true, count: 0 })
      expect(result.flag).toBe(true)
      expect(result.count).toBe(0)
    })
  })

  describe("discoverPaths", () => {
    it("discovers all leaf paths", () => {
      const obj = {
        name: "test",
        nested: { amount: 1.5, status: "ok" },
        items: ["a", "b"],
      }
      const paths = discoverPaths(obj)
      expect(paths).toContain("name")
      expect(paths).toContain("nested.amount")
      expect(paths).toContain("nested.status")
      expect(paths).toContain("items[0]")
      expect(paths).toContain("items[1]")
    })

    it("returns sorted paths", () => {
      const paths = discoverPaths({ z: 1, a: 2, m: 3 })
      expect(paths).toEqual(["a", "m", "z"])
    })
  })

  describe("formatCellValue", () => {
    it("formats dates", () => {
      const result = formatCellValue("2024-01-15T10:30:00Z", "date")
      expect(result).toBeTruthy()
      expect(result).not.toBe("")
    })

    it("formats numbers", () => {
      expect(formatCellValue(1234.5, "number")).toBeTruthy()
    })

    it("formats JSON objects", () => {
      const result = formatCellValue({ a: 1 }, "json")
      expect(result).toContain('"a"')
    })

    it("formats null/undefined as empty string", () => {
      expect(formatCellValue(null)).toBe("")
      expect(formatCellValue(undefined)).toBe("")
    })

    it("uses text as default formatter", () => {
      expect(formatCellValue("hello")).toBe("hello")
      expect(formatCellValue(42)).toBe("42")
    })

    it("handles invalid date gracefully", () => {
      const result = formatCellValue("not-a-date", "date")
      expect(result).toBe("not-a-date")
    })

    it("handles NaN number gracefully", () => {
      expect(formatCellValue("abc", "number")).toBe("abc")
    })

    it("formats zero correctly", () => {
      const result = formatCellValue(0, "number")
      expect(result).toBeTruthy()
    })

    it("formats boolean values", () => {
      expect(formatCellValue(true)).toBe("true")
      expect(formatCellValue(false)).toBe("false")
    })

    it("formats arrays as JSON", () => {
      const result = formatCellValue([1, 2], "json")
      expect(result).toContain("1")
      expect(result).toContain("2")
    })

    it("formats empty object", () => {
      expect(formatCellValue({}, "json")).toBe("{}")
    })
  })
})
