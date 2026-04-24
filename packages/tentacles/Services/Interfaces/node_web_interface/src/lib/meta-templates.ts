/**
 * Meta templates compose ordered base templates into new templates.
 *
 * Each step can override param values (applied as defaultValue) and mark
 * params as hidden (excluded from the UI but still included in task content).
 *
 * Resolved meta templates are plain ActionTemplate objects — the rest of the
 * system is unaware of the distinction.
 */

import { z } from "zod"

import {
  type ActionParamDef,
  type ActionTemplate,
  BASE_ACTION_TEMPLATES,
} from "./action-templates"

export interface MetaTemplateStep {
  /** ID of a base template to include */
  templateId: string
  /** Param key → value to force as defaultValue */
  overrides?: Record<string, string>
  /** Param keys to hide from the UI */
  hiddenParams?: string[]
}

export interface MetaTemplateDef {
  id: string
  label: string
  description: string
  steps: MetaTemplateStep[]
}

/**
 * Resolve a MetaTemplateDef into a flat ActionTemplate.
 *
 * - Params are merged in step order; first-occurrence-wins on duplicate keys.
 * - overrides are applied as defaultValue on the matching param.
 * - hiddenParams sets hidden:true; a hidden+required param without a
 *   defaultValue/override is an error (it would silently block submission).
 */
export function resolveMetaTemplate(def: MetaTemplateDef): ActionTemplate {
  const seenKeys = new Set<string>()
  const mergedParams: ActionParamDef[] = []
  const actionTypes: string[] = []

  for (const step of def.steps) {
    const base = BASE_ACTION_TEMPLATES.find((t) => t.id === step.templateId)
    if (!base) {
      throw new Error(
        `Meta template "${def.id}" references unknown template "${step.templateId}"`,
      )
    }

    for (const actionType of base.actionTypes) {
      if (!actionTypes.includes(actionType)) {
        actionTypes.push(actionType)
      }
    }

    for (const param of base.params) {
      if (seenKeys.has(param.key)) continue
      seenKeys.add(param.key)

      const override = step.overrides?.[param.key]
      const isHidden = step.hiddenParams?.includes(param.key) ?? false

      if (isHidden && param.required && override === undefined && !param.defaultValue) {
        throw new Error(
          `Meta template "${def.id}": param "${param.key}" is hidden and required but has no default value or override`,
        )
      }

      mergedParams.push({
        ...param,
        ...(override !== undefined ? { defaultValue: override } : {}),
        ...(isHidden ? { hidden: true } : {}),
      })
    }
  }

  return {
    id: def.id,
    label: def.label,
    description: def.description,
    actionTypes,
    params: mergedParams,
  }
}

const MetaTemplateStepSchema = z.object({
  templateId: z.string().min(1),
  overrides: z.record(z.string(), z.string()).optional(),
  hiddenParams: z.array(z.string()).optional(),
})

const MetaTemplateDefSchema = z.object({
  id: z.string().min(1),
  label: z.string().min(1),
  description: z.string(),
  steps: z.array(MetaTemplateStepSchema).min(1),
})

export function validateMetaTemplateJson(json: unknown): MetaTemplateDef {
  return MetaTemplateDefSchema.parse(json)
}

const STORAGE_KEY = "user_meta_templates"

const RESERVED_IDS: ReadonlySet<string> = new Set(
  BASE_ACTION_TEMPLATES.map((t) => t.id),
)

export function loadUserMetaTemplates(): MetaTemplateDef[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.flatMap((item) => {
      const result = MetaTemplateDefSchema.safeParse(item)
      return result.success ? [result.data] : []
    })
  } catch {
    return []
  }
}

export function saveUserMetaTemplate(def: MetaTemplateDef): void {
  if (RESERVED_IDS.has(def.id)) {
    throw new Error(
      `Template ID "${def.id}" is reserved and cannot be used for user templates`,
    )
  }
  const existing = loadUserMetaTemplates()
  const updated = existing.filter((t) => t.id !== def.id)
  updated.push(def)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
}

export function deleteUserMetaTemplate(id: string): void {
  const existing = loadUserMetaTemplates()
  const updated = existing.filter((t) => t.id !== id)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
}

/**
 * Returns all templates: base + user-imported meta (resolved).
 * Safe to call on every render — user templates are read from localStorage.
 */
export function getAllTemplates(): ActionTemplate[] {
  const userDefs = loadUserMetaTemplates()
  const resolvedUser = userDefs.flatMap((def) => {
    try {
      return [resolveMetaTemplate(def)]
    } catch {
      return []
    }
  })
  return [...BASE_ACTION_TEMPLATES, ...resolvedUser]
}

/**
 * Find a template by ID across base and user-imported templates.
 */
export function getTemplateById(id: string): ActionTemplate | undefined {
  return getAllTemplates().find((t) => t.id === id)
}

const LAST_USED_KEY = "last_used_import_template"

export function getLastUsedImportTemplateId(): string | null {
  const id = localStorage.getItem(LAST_USED_KEY)
  if (!id) return null
  return getAllTemplates().some((t) => t.id === id) ? id : null
}

export function setLastUsedImportTemplateId(id: string): void {
  localStorage.setItem(LAST_USED_KEY, id)
}
