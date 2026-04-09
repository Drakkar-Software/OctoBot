import { AlertCircle, CheckCircle2 } from "lucide-react"
import { useMemo } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardHeader,
} from "@/components/ui/card"
import { getTemplateById } from "@/lib/action-templates"
import type { ActionRow } from "./ColumnMappingStep"

export interface ReviewStepProps {
  actions: ActionRow[]
  onNext: () => void
  onBack: () => void
}

interface ValidationResult {
  isValid: boolean
  missingParams: string[]
}

function validateAction(action: ActionRow): ValidationResult {
  const template = getTemplateById(action.templateId)
  if (!template) return { isValid: false, missingParams: ["Unknown template"] }

  const missingParams: string[] = []
  for (const param of template.params) {
    if (param.required) {
      const value = action.paramValues[param.key]?.trim()
      if (!value) {
        missingParams.push(param.label)
      }
    }
  }

  return {
    isValid: missingParams.length === 0,
    missingParams,
  }
}

export default function ReviewStep({
  actions,
  onNext,
  onBack,
}: ReviewStepProps) {
  const validations = useMemo(
    () => actions.map((action) => ({
      action,
      validation: validateAction(action),
    })),
    [actions],
  )

  const validCount = validations.filter((v) => v.validation.isValid).length
  const invalidCount = validations.filter((v) => !v.validation.isValid).length
  const allValid = invalidCount === 0

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="text-sm font-medium">
          {actions.length} action{actions.length !== 1 ? "s" : ""} ready for
          import
        </p>
        <p className="text-xs text-muted-foreground">
          {validCount} valid
          {invalidCount > 0 && (
            <span className="text-destructive">
              , {invalidCount} with missing required parameters
            </span>
          )}
        </p>
      </div>

      <div className="max-h-[50vh] overflow-auto space-y-2">
        {validations.map(({ action, validation }) => {
          const template = getTemplateById(action.templateId)
          const filledCount = Object.values(action.paramValues).filter(
            (v) => v.trim() !== "",
          ).length
          const totalParams = template?.params.length ?? 0

          return (
            <Card
              key={action.rowIndex}
              className={
                validation.isValid
                  ? ""
                  : "border-destructive/50"
              }
            >
              <CardHeader className="py-2 px-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {validation.isValid ? (
                      <CheckCircle2 className="size-4 text-green-500" />
                    ) : (
                      <AlertCircle className="size-4 text-destructive" />
                    )}
                    <span className="text-sm font-medium">{action.name}</span>
                    <Badge variant="secondary" className="text-xs">
                      {template?.label ?? action.templateId}
                    </Badge>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {filledCount}/{totalParams} params filled
                  </span>
                </div>
              </CardHeader>
              <CardContent className="py-2 px-4">
                <div className="flex flex-wrap gap-x-4 gap-y-1">
                  {template?.params
                    .filter((p) => action.paramValues[p.key]?.trim())
                    .map((param) => (
                      <span key={param.key} className="text-xs">
                        <span className="text-muted-foreground">
                          {param.label}:
                        </span>{" "}
                        <span className="font-mono">
                          {param.sensitive
                            ? "\u2022\u2022\u2022\u2022\u2022\u2022"
                            : action.paramValues[param.key]}
                        </span>
                      </span>
                    ))}
                </div>
                {!validation.isValid && (
                  <p className="text-xs text-destructive mt-1">
                    Missing: {validation.missingParams.join(", ")}
                  </p>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>

      <div className="flex gap-2 justify-end">
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>
        <Button
          onClick={onNext}
          disabled={validCount === 0}
        >
          Review {validCount} Action{validCount !== 1 ? "s" : ""}
        </Button>
      </div>
    </div>
  )
}
