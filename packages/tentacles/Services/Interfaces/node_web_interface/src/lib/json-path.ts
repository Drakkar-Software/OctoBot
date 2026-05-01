/**
 * JSON path utilities for extracting, flattening, and discovering
 * paths within nested JSON objects. Used by the export flow to
 * map bot result JSON into readable table columns.
 */

/**
 * Extract a value from a nested object using dot-notation path.
 * Supports array indexing with bracket notation: "items[0].name"
 */
const DANGEROUS_KEYS = new Set(["__proto__", "constructor", "prototype"])
const EARLIEST_VALID_DATE_MS = 956256098000 // April 20, 2000 at 18:41:38

export function extractValue(obj: unknown, path: string): unknown {
  if (obj === null || obj === undefined) return undefined

  const segments = path.replace(/\[(\d+)]/g, ".$1").split(".")
  let current: unknown = obj

  for (const segment of segments) {
    if (current === null || current === undefined) return undefined
    if (DANGEROUS_KEYS.has(segment)) return undefined
    if (typeof current === "object") {
      current = (current as Record<string, unknown>)[segment]
    } else {
      return undefined
    }
  }

  return current
}

/**
 * Flatten a nested JSON object into a flat Record with dot-notation keys.
 * Arrays are expanded with bracket indices: { items: [{ a: 1 }] } → { "items[0].a": 1 }
 */
export function flattenJSON(
  obj: unknown,
  prefix = "",
  maxDepth = 8,
): Record<string, unknown> {
  const result: Record<string, unknown> = {}

  function recurse(current: unknown, currentPrefix: string, depth: number) {
    if (depth > maxDepth) {
      result[currentPrefix] = current
      return
    }

    if (current === null || current === undefined) {
      result[currentPrefix] = current
      return
    }

    if (Array.isArray(current)) {
      if (current.length === 0) {
        result[currentPrefix] = current
        return
      }
      for (let i = 0; i < current.length; i++) {
        recurse(current[i], `${currentPrefix}[${i}]`, depth + 1)
      }
      return
    }

    if (typeof current === "object") {
      const entries = Object.entries(current as Record<string, unknown>)
      if (entries.length === 0) {
        result[currentPrefix] = current
        return
      }
      for (const [key, value] of entries) {
        if (DANGEROUS_KEYS.has(key)) continue
        const newPrefix = currentPrefix ? `${currentPrefix}.${key}` : key
        recurse(value, newPrefix, depth + 1)
      }
      return
    }

    result[currentPrefix] = current
  }

  recurse(obj, prefix, 0)
  return result
}

/**
 * Discover all leaf paths in a JSON object. Returns an array of
 * dot-notation path strings sorted alphabetically.
 */
export function discoverPaths(obj: unknown): string[] {
  const flat = flattenJSON(obj)
  return Object.keys(flat).sort()
}

/**
 * Format a value for display in a table cell.
 */
export function formatCellValue(
  value: unknown,
  formatter?: "date" | "number" | "json" | "text",
): string {
  if (value === null || value === undefined) return ""

  switch (formatter) {
    case "date": {
      try {
        const nbValue = Number(value)
        const date_ms =
          nbValue < EARLIEST_VALID_DATE_MS ? nbValue * 1000 : nbValue
        return new Intl.DateTimeFormat(undefined, {
          month: "short",
          day: "numeric",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        }).format(new Date(date_ms))
      } catch {
        return String(value)
      }
    }
    case "number": {
      const num = Number(value)
      return Number.isNaN(num)
        ? String(value)
        : num > 1
          ? num.toLocaleString()
          : String(num)
    }
    case "json":
      return typeof value === "object"
        ? JSON.stringify(value, null, 2)
        : String(value)
    default:
      return typeof value === "object" ? JSON.stringify(value) : String(value)
  }
}
