import { describe, expect, it } from "vitest"

import { parseCSVRaw, generateCSV, isValidCSVFile, escapeCSVValue } from "../csv"

describe("parseCSVRaw", () => {
  it("parses simple CSV with headers and rows", () => {
    const csv = `name,amount,address
Task1,1.5,0x1234567890123456789012345678901234567890
Task2,2.0,0xABCDEF1234567890ABCDEF1234567890ABCDEF12`

    const result = parseCSVRaw(csv)
    expect(result.headers).toEqual(["name", "amount", "address"])
    expect(result.rows).toHaveLength(2)
    expect(result.rows[0]).toEqual([
      "Task1",
      "1.5",
      "0x1234567890123456789012345678901234567890",
    ])
  })

  it("handles quoted fields with commas", () => {
    const csv = `name,description,value
"Task 1","has a, comma",100`

    const result = parseCSVRaw(csv)
    expect(result.headers).toEqual(["name", "description", "value"])
    expect(result.rows[0][0]).toBe("Task 1")
    expect(result.rows[0][1]).toBe("has a, comma")
    expect(result.rows[0][2]).toBe("100")
  })

  it("handles escaped quotes", () => {
    const csv = `name,value
"has ""quotes""",123`

    const result = parseCSVRaw(csv)
    expect(result.rows[0][0]).toBe('has "quotes"')
  })

  it("skips empty lines", () => {
    const csv = `name,value
row1,1

row2,2
`

    const result = parseCSVRaw(csv)
    expect(result.rows).toHaveLength(2)
  })

  it("throws on empty CSV", () => {
    expect(() => parseCSVRaw("")).toThrow()
  })

  it("throws on header-only CSV", () => {
    const result = parseCSVRaw("name,value")
    expect(result.headers).toEqual(["name", "value"])
    expect(result.rows).toHaveLength(0)
  })

  it("handles single column CSV", () => {
    const csv = `address
0x1234567890123456789012345678901234567890`

    const result = parseCSVRaw(csv)
    expect(result.headers).toEqual(["address"])
    expect(result.rows).toHaveLength(1)
  })

  it("does not require name or type columns", () => {
    const csv = `custom_field,another_field
val1,val2`

    const result = parseCSVRaw(csv)
    expect(result.headers).toEqual(["custom_field", "another_field"])
    expect(result.rows).toHaveLength(1)
  })

  it("handles duplicate header names", () => {
    const csv = `a,a,a
1,2,3`

    const result = parseCSVRaw(csv)
    expect(result.headers).toEqual(["a", "a", "a"])
    expect(result.rows[0]).toEqual(["1", "2", "3"])
  })

  it("handles rows with more fields than headers", () => {
    const csv = `a,b
1,2,3,4`

    const result = parseCSVRaw(csv)
    expect(result.rows[0]).toEqual(["1", "2", "3", "4"])
  })

  it("handles rows with fewer fields than headers", () => {
    const csv = `a,b,c
1`

    const result = parseCSVRaw(csv)
    expect(result.rows[0]).toEqual(["1"])
  })

  it("handles unicode content", () => {
    const csv = `name,value
"cafe\u0301",42`

    const result = parseCSVRaw(csv)
    // The raw parser preserves the input as-is
    expect(result.rows[0][0]).toBe("cafe\u0301")
  })

  it("handles Windows CRLF line endings", () => {
    const csv = "name,value\r\nAlice,100\r\nBob,200"
    const result = parseCSVRaw(csv)
    expect(result.headers).toEqual(["name", "value"])
    expect(result.rows).toHaveLength(2)
    expect(result.rows[0]).toEqual(["Alice", "100"])
    expect(result.rows[1]).toEqual(["Bob", "200"])
  })

  it("handles old Mac CR line endings", () => {
    const csv = "name,value\rAlice,100\rBob,200"
    const result = parseCSVRaw(csv)
    expect(result.headers).toEqual(["name", "value"])
    expect(result.rows).toHaveLength(2)
  })

  it("handles whitespace-only lines after header", () => {
    const csv = `a,b

1,2`

    const result = parseCSVRaw(csv)
    // whitespace-only lines are skipped
    expect(result.rows).toHaveLength(1)
    expect(result.rows[0]).toEqual(["1", "2"])
  })
})

describe("generateCSV", () => {
  it("generates CSV from headers and rows", () => {
    const csv = generateCSV(["name", "value"], [["Alice", "100"], ["Bob", "200"]])
    expect(csv).toBe("name,value\nAlice,100\nBob,200")
  })

  it("generates CSV with only headers and no rows", () => {
    const csv = generateCSV(["a", "b"], [])
    expect(csv).toBe("a,b")
  })

  it("escapes special characters in generated CSV", () => {
    const csv = generateCSV(["name"], [["has, comma"], ['has "quotes"']])
    expect(csv).toContain('"has, comma"')
    expect(csv).toContain('"has ""quotes"""')
  })

  it("handles null and undefined values in rows", () => {
    const csv = generateCSV(["a"], [[null], [undefined]])
    expect(csv).toBe("a\n\n")
  })

  it("escapes formula injection in generated CSV", () => {
    const csv = generateCSV(["formula"], [["=SUM(A1)"]])
    expect(csv).toContain("'=SUM(A1)")
  })
})

describe("isValidCSVFile", () => {
  it("accepts .csv files", () => {
    const file = new File([""], "data.csv", { type: "text/csv" })
    expect(isValidCSVFile(file)).toBe(true)
  })

  it("accepts uppercase .CSV extension", () => {
    const file = new File([""], "DATA.CSV", { type: "text/csv" })
    expect(isValidCSVFile(file)).toBe(true)
  })

  it("accepts mixed case .Csv extension", () => {
    const file = new File([""], "file.Csv", { type: "text/csv" })
    expect(isValidCSVFile(file)).toBe(true)
  })

  it("rejects non-CSV files", () => {
    const file = new File([""], "data.txt", { type: "text/plain" })
    expect(isValidCSVFile(file)).toBe(false)
  })

  it("rejects files with csv in name but different extension", () => {
    const file = new File([""], "csv_data.json", { type: "application/json" })
    expect(isValidCSVFile(file)).toBe(false)
  })
})

describe("escapeCSVValue", () => {
  it("wraps values containing commas in quotes", () => {
    expect(escapeCSVValue("a,b")).toBe('"a,b"')
  })

  it("wraps values containing newlines in quotes", () => {
    expect(escapeCSVValue("line1\nline2")).toBe('"line1\nline2"')
  })

  it("wraps values containing carriage returns in quotes", () => {
    expect(escapeCSVValue("line1\rline2")).toBe('"line1\rline2"')
  })

  it("escapes double quotes within values", () => {
    expect(escapeCSVValue('say "hello"')).toBe('"say ""hello"""')
  })

  it("returns plain value when no special chars", () => {
    expect(escapeCSVValue("simple")).toBe("simple")
  })

  it("converts numbers to strings", () => {
    expect(escapeCSVValue(42)).toBe("42")
    expect(escapeCSVValue(3.14)).toBe("3.14")
  })

  it("converts booleans to strings", () => {
    expect(escapeCSVValue(true)).toBe("true")
    expect(escapeCSVValue(false)).toBe("false")
  })
})
