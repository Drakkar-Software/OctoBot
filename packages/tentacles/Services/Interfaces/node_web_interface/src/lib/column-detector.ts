/**
 * Smart column detection and template auto-detection for CSV import.
 *
 * Two-phase approach:
 * 1. Score each CSV column against each ActionParamDef (value pattern + fuzzy header match)
 * 2. Score each ActionTemplate per row by how many required params are satisfied
 */

import {
  type ActionParamDef,
  type ActionTemplate,
} from "./action-templates"
import { getAllTemplates } from "./meta-templates"

// ── Types ──────────────────────────────────────────────────────────────

export interface ColumnScore {
  columnIndex: number
  paramKey: string
  score: number
}

export interface ColumnMapping {
  /** CSV column index → param key */
  columnIndex: number
  paramKey: string
  confidence: "high" | "medium" | "low"
}

export interface RowDetectionResult {
  templateId: string
  templateScore: number
  mappings: ColumnMapping[]
  /** Param values extracted from the CSV row based on mappings */
  paramValues: Record<string, string>
  /** Column indices that were not mapped to any param */
  unmappedColumns: number[]
}

// ── Scoring weights ────────────────────────────────────────────────────

const VALUE_PATTERN_WEIGHT = 10
const HEADER_EXACT_WEIGHT = 8
const HEADER_FUZZY_WEIGHT = 5
const REQUIRED_PARAM_BONUS = 2

// ── Column header normalization ────────────────────────────────────────

function normalizeHeader(header: string): string {
  return header
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "")
}

function normalizeAlias(alias: string): string {
  return alias
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "")
}

// ── Value pattern scoring ──────────────────────────────────────────────

/**
 * Test a column's values against a param's detection patterns.
 * Returns a score based on what fraction of non-empty values match.
 */
function scoreValuePatterns(
  columnValues: string[],
  param: ActionParamDef,
): number {
  if (!param.detectPatterns || param.detectPatterns.length === 0) return 0

  const nonEmpty = columnValues.filter((v) => v.trim() !== "")
  if (nonEmpty.length === 0) return 0

  let matchCount = 0
  for (const value of nonEmpty) {
    const trimmed = value.trim()
    for (const pattern of param.detectPatterns) {
      if (pattern.test(trimmed)) {
        matchCount++
        break
      }
    }
  }

  const ratio = matchCount / nonEmpty.length
  return ratio * VALUE_PATTERN_WEIGHT
}

// ── Header fuzzy scoring ───────────────────────────────────────────────

function scoreHeaderMatch(
  header: string,
  param: ActionParamDef,
): number {
  const normalized = normalizeHeader(header)

  // Exact key match (highest confidence)
  if (normalized === normalizeAlias(param.key)) {
    return HEADER_EXACT_WEIGHT
  }

  // Fuzzy alias match
  if (param.aliasFuzzy) {
    for (const alias of param.aliasFuzzy) {
      const normAlias = normalizeAlias(alias)
      if (normalized === normAlias) return HEADER_FUZZY_WEIGHT
      if (normalized.includes(normAlias) || normAlias.includes(normalized)) {
        return HEADER_FUZZY_WEIGHT * 0.7
      }
    }
  }

  return 0
}

// ── Column-to-param scoring matrix ─────────────────────────────────────

/**
 * Build a scoring matrix: for each (column, param) pair, compute a combined score.
 */
function buildScoringMatrix(
  headers: string[],
  columnValues: string[][],
  params: ActionParamDef[],
): ColumnScore[] {
  const scores: ColumnScore[] = []

  for (let colIdx = 0; colIdx < headers.length; colIdx++) {
    const values = columnValues[colIdx] ?? []
    const header = headers[colIdx] ?? ""

    for (const param of params) {
      const valueScore = scoreValuePatterns(values, param)
      const headerScore = scoreHeaderMatch(header, param)

      // Only consider this pair if there's actual evidence (value or header match)
      if (valueScore > 0 || headerScore > 0) {
        const total = valueScore + headerScore + (param.required ? REQUIRED_PARAM_BONUS : 0)
        scores.push({
          columnIndex: colIdx,
          paramKey: param.key,
          score: total,
        })
      }
    }
  }

  return scores.sort((a, b) => b.score - a.score)
}

/**
 * Greedily assign columns to params using the scoring matrix.
 * Each column maps to at most one param, each param to at most one column.
 */
function assignMappings(
  scores: ColumnScore[],
): ColumnMapping[] {
  const usedColumns = new Set<number>()
  const usedParams = new Set<string>()
  const mappings: ColumnMapping[] = []

  for (const entry of scores) {
    if (usedColumns.has(entry.columnIndex) || usedParams.has(entry.paramKey)) {
      continue
    }

    let confidence: "high" | "medium" | "low"
    if (entry.score >= VALUE_PATTERN_WEIGHT + HEADER_FUZZY_WEIGHT) {
      confidence = "high"
    } else if (entry.score >= HEADER_FUZZY_WEIGHT) {
      confidence = "medium"
    } else {
      confidence = "low"
    }

    mappings.push({
      columnIndex: entry.columnIndex,
      paramKey: entry.paramKey,
      confidence,
    })

    usedColumns.add(entry.columnIndex)
    usedParams.add(entry.paramKey)
  }

  return mappings
}

// ── Template scoring per row ───────────────────────────────────────────

function scoreTemplateForRow(
  template: ActionTemplate,
  mappings: ColumnMapping[],
): number {
  const mappingByKey = new Map(mappings.map((m) => [m.paramKey, m]))
  let score = 0

  // Hidden params have pre-set defaults and are invisible to the user — exclude from scoring
  const visibleParams = template.params.filter((p) => !p.hidden)

  for (const param of visibleParams) {
    const mapping = mappingByKey.get(param.key)
    if (mapping) {
      // Weight by confidence: high = 5, medium = 3, low = 1
      const confidenceWeight =
        mapping.confidence === "high" ? 5 : mapping.confidence === "medium" ? 3 : 1
      score += confidenceWeight * (param.required ? 2 : 1)
    } else if (param.required) {
      score -= 4
    }
  }

  // Penalize templates that have many params not matching — favors simpler/better-fitting templates
  const unmatchedOptional = visibleParams.filter(
    (p) => !p.required && !mappingByKey.has(p.key),
  ).length
  score -= unmatchedOptional * 0.5

  return score
}

// ── Public API ─────────────────────────────────────────────────────────

/**
 * Extract column values from rows (transpose: rows × cols → cols × rows).
 */
export function extractColumnValues(
  headers: string[],
  rows: string[][],
): string[][] {
  return headers.map((_, colIdx) =>
    rows.map((row) => row[colIdx] ?? ""),
  )
}

/**
 * Detect the best template and column mappings for a CSV dataset.
 * Returns one result per row, each with its best-matching template.
 *
 * For efficiency, column scoring is done once globally, then template
 * scoring is per-template (not per-row) since all rows share the same headers.
 */
export function detectColumnsAndTemplates(
  headers: string[],
  rows: string[][],
): RowDetectionResult[] {
  const columnValues = extractColumnValues(headers, rows)

  // Score and assign mappings for each template (hidden params excluded from scoring)
  const templateResults = getAllTemplates().map((template) => {
    const visibleParams = template.params.filter((p) => !p.hidden)
    const scores = buildScoringMatrix(headers, columnValues, visibleParams)
    const mappings = assignMappings(scores)
    const templateScore = scoreTemplateForRow(template, mappings)
    return { template, mappings, templateScore }
  })

  // Pick the best template (global for now, applied to all rows)
  templateResults.sort((a, b) => b.templateScore - a.templateScore)
  const best = templateResults[0]

  if (!best) {
    return rows.map(() => ({
      templateId: getAllTemplates()[0]?.id ?? "transfer",
      templateScore: 0,
      mappings: [],
      paramValues: {},
      unmappedColumns: headers.map((_, i) => i),
    }))
  }

  // Apply the best template to each row
  return rows.map((row) => {
    const paramValues: Record<string, string> = {}
    const mappedColumnIndices = new Set<number>()

    for (const mapping of best.mappings) {
      const value = row[mapping.columnIndex]?.trim() ?? ""
      if (value) {
        paramValues[mapping.paramKey] = value
      }
      mappedColumnIndices.add(mapping.columnIndex)
    }
    for (const param of best.template.params) {
      if (!paramValues[param.key] && param.defaultValue) {
        paramValues[param.key] = param.defaultValue
      }
    }

    const unmappedColumns = headers
      .map((_, i) => i)
      .filter((i) => !mappedColumnIndices.has(i))

    return {
      templateId: best.template.id,
      templateScore: best.templateScore,
      mappings: best.mappings,
      paramValues,
      unmappedColumns,
    }
  })
}

/**
 * Re-detect column mappings for a specific template (when user changes
 * the template for a row).
 */
export function detectMappingsForTemplate(
  template: ActionTemplate,
  headers: string[],
  rows: string[][],
): ColumnMapping[] {
  const columnValues = extractColumnValues(headers, rows)
  const visibleParams = template.params.filter((p) => !p.hidden)
  const scores = buildScoringMatrix(headers, columnValues, visibleParams)
  return assignMappings(scores)
}

/**
 * Build param values for a single row given mappings.
 * When a template is provided, applies defaultValue for params not filled by mappings.
 */
export function buildParamValuesForRow(
  row: string[],
  mappings: ColumnMapping[],
  template?: ActionTemplate,
): Record<string, string> {
  const values: Record<string, string> = {}
  for (const mapping of mappings) {
    const value = row[mapping.columnIndex]?.trim() ?? ""
    if (value) {
      values[mapping.paramKey] = value
    }
  }
  if (template) {
    for (const param of template.params) {
      if (!values[param.key] && param.defaultValue) {
        values[param.key] = param.defaultValue
      }
    }
  }
  return values
}
