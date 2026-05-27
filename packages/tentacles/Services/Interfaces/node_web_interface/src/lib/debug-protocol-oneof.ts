function isOneOfEnvelope(record: Record<string, unknown>): boolean {
  if ("actual_instance" in record) return true
  if ("one_of_schemas" in record) return true
  if ("discriminator_value_class_map" in record) return true
  for (const key of Object.keys(record)) {
    if (key.startsWith("oneof_schema_") && key.endsWith("_validator")) {
      return true
    }
  }
  return false
}

/** Resolves the active variant from an OpenAPI oneOf wrapper (generated client shape). */
export function resolveOneOfInstance<T extends object>(
  wrapper: object | null | undefined,
): T | null {
  if (!wrapper || typeof wrapper !== "object") return null

  const record = wrapper as Record<string, unknown>
  const actualInstance = record.actual_instance
  if (actualInstance && typeof actualInstance === "object") {
    return actualInstance as T
  }

  // Protocol/API payloads often embed the variant directly (see UserActionConfiguration.to_dict).
  if (!isOneOfEnvelope(record)) {
    return record as T
  }

  for (const [key, value] of Object.entries(record)) {
    if (!key.startsWith("oneof_schema_") || !key.endsWith("_validator")) {
      continue
    }
    if (value && typeof value === "object") {
      return value as T
    }
  }

  return null
}
