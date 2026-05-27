import { describe, expect, it } from "vitest"

import {
  childNodesAreCollapsible,
  formatJsonCollectionSummary,
  formatJsonForClipboard,
  formatJsonPrimitive,
  getJsonCollectionEntries,
  getVisibleJsonObjectEntries,
  isJsonCollection,
} from "@/components/ui/collapsible-json-view"

describe("formatJsonPrimitive", () => {
  it("formats null and booleans", () => {
    expect(formatJsonPrimitive(null)).toBe("null")
    expect(formatJsonPrimitive(true)).toBe("true")
    expect(formatJsonPrimitive(false)).toBe("false")
  })

  it("JSON-encodes strings", () => {
    expect(formatJsonPrimitive("hello")).toBe('"hello"')
  })

  it("formats numbers", () => {
    expect(formatJsonPrimitive(42)).toBe("42")
  })
})

describe("isJsonCollection", () => {
  it("returns true for objects and arrays", () => {
    expect(isJsonCollection({})).toBe(true)
    expect(isJsonCollection([])).toBe(true)
  })

  it("returns false for primitives", () => {
    expect(isJsonCollection(null)).toBe(false)
    expect(isJsonCollection("x")).toBe(false)
  })
})

describe("formatJsonForClipboard", () => {
  it("pretty-prints JSON for clipboard", () => {
    expect(formatJsonForClipboard({ a: 1 })).toBe('{\n  "a": 1\n}')
    expect(formatJsonForClipboard([1, 2])).toBe("[\n  1,\n  2\n]")
  })
})

describe("getVisibleJsonObjectEntries", () => {
  it("omits _updated_fields from object entries", () => {
    expect(
      getVisibleJsonObjectEntries({
        a: 1,
        _updated_fields: ["a"],
        b: 2,
      }),
    ).toEqual([
      ["a", 1],
      ["b", 2],
    ])
  })
})

describe("getJsonCollectionEntries", () => {
  it("filters hidden fields only on objects", () => {
    expect(getJsonCollectionEntries([{ _updated_fields: [] }])).toEqual([
      ["0", { _updated_fields: [] }],
    ])
  })
})

describe("childNodesAreCollapsible", () => {
  it("returns false for array children only", () => {
    expect(childNodesAreCollapsible([1, 2])).toBe(false)
    expect(childNodesAreCollapsible({ a: 1 })).toBe(true)
  })
})

describe("formatJsonCollectionSummary", () => {
  it("summarizes array and object lengths", () => {
    expect(formatJsonCollectionSummary([1, 2, 3])).toBe("[3]")
    expect(formatJsonCollectionSummary({ a: 1, b: 2 })).toBe("{2}")
  })

  it("summarizes empty collections", () => {
    expect(formatJsonCollectionSummary([])).toBe("[0]")
    expect(formatJsonCollectionSummary({})).toBe("{0}")
  })

  it("excludes hidden fields from object length", () => {
    expect(
      formatJsonCollectionSummary({
        a: 1,
        _updated_fields: [],
      }),
    ).toBe("{1}")
  })
})
