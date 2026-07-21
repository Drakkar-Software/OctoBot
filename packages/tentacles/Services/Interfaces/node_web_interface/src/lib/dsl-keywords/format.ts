import type { DslParameter } from "@/client"

export function formatDslParameterSummary(parameter: DslParameter): string {
  const label = parameter.label?.trim() || parameter.name
  return `${label}[${parameter.value_type}]`
}

export function formatDslParametersList(
  parameters: DslParameter[] | undefined,
): string {
  const list = parameters ?? []
  if (!list.length) return "0: —"
  return `${list.length}: ${list.map(formatDslParameterSummary).join(", ")}`
}
