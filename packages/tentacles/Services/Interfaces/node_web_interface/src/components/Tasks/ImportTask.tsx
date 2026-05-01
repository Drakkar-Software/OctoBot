import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { type Task_Input as Task, TasksService } from "@/client"
import useCustomToast from "@/hooks/useCustomToast"
import type { CSVRawResult } from "@/lib/csv"

import CsvUploadStep from "./ImportSteps/CsvUploadStep"
import ColumnMappingStep, {
  type ActionRow,
} from "./ImportSteps/ColumnMappingStep"
import EncryptStep from "./ImportSteps/EncryptStep"
import ReviewStep from "./ImportSteps/ReviewStep"

export interface ImportTaskProps {
  onSuccess?: () => void
}

type ImportStep = "upload" | "mapping" | "review" | "encrypt"

const STEP_LABELS: Record<ImportStep, string> = {
  upload: "Upload CSV",
  mapping: "Map Columns",
  review: "Review",
  encrypt: "Import",
}

const STEPS: ImportStep[] = ["upload", "mapping", "review", "encrypt"]

export default function ImportTask({ onSuccess }: ImportTaskProps) {
  const [currentStep, setCurrentStep] = useState<ImportStep>("upload")
  const [csvData, setCsvData] = useState<CSVRawResult | null>(null)
  const [actionRows, setActionRows] = useState<ActionRow[]>([])
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const createTaskMutation = useMutation({
    mutationFn: (data: Array<Task>) =>
      TasksService.createTasks({ requestBody: data }),
  })

  const handleCsvParsed = (result: CSVRawResult) => {
    setCsvData(result)
    setCurrentStep("mapping")
  }

  const handleMappingConfirm = (rows: ActionRow[]) => {
    setActionRows(rows)
    setCurrentStep("review")
  }

  const handleImport = async (tasks: Task[]) => {
    if (tasks.length === 0) {
      showErrorToast("No actions to import")
      return
    }

    try {
      const result = await createTaskMutation.mutateAsync(tasks)
      const [successCount, errorCount] = result as [number, number]

      if (successCount > 0) {
        showSuccessToast(
          `Successfully imported ${successCount} action${successCount > 1 ? "s" : ""}${
            errorCount > 0 ? ` (${errorCount} failed)` : ""
          }`,
        )
      } else {
        showErrorToast("Failed to import actions")
      }

      queryClient.invalidateQueries({ queryKey: ["tasks"] })
      onSuccess?.()
    } catch {
      showErrorToast("An error occurred during import")
    }
  }

  const currentStepIndex = STEPS.indexOf(currentStep)

  return (
    <div className="flex flex-col gap-6">
      {/* Step indicator */}
      <div className="flex items-center gap-2">
        {STEPS.map((step, index) => {
          const isActive = index === currentStepIndex
          const isCompleted = index < currentStepIndex

          return (
            <div key={step} className="flex items-center gap-2">
              {index > 0 && (
                <div
                  className={`h-px w-8 ${
                    isCompleted ? "bg-primary" : "bg-border"
                  }`}
                />
              )}
              <div className="flex items-center gap-1.5">
                <div
                  className={`flex size-6 items-center justify-center rounded-full text-xs font-medium ${
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : isCompleted
                        ? "bg-primary/20 text-primary"
                        : "bg-muted text-muted-foreground"
                  }`}
                >
                  {index + 1}
                </div>
                <span
                  className={`text-xs ${
                    isActive
                      ? "font-medium text-foreground"
                      : "text-muted-foreground"
                  }`}
                >
                  {STEP_LABELS[step]}
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Step content */}
      {currentStep === "upload" && (
        <CsvUploadStep onParsed={handleCsvParsed} />
      )}

      {currentStep === "mapping" && csvData && (
        <ColumnMappingStep
          headers={csvData.headers}
          rows={csvData.rows}
          onConfirm={handleMappingConfirm}
          onBack={() => setCurrentStep("upload")}
        />
      )}

      {currentStep === "review" && (
        <ReviewStep
          actions={actionRows}
          onNext={() => setCurrentStep("encrypt")}
          onBack={() => setCurrentStep("mapping")}
        />
      )}

      {currentStep === "encrypt" && (
        <EncryptStep
          actions={actionRows}
          onImport={handleImport}
          onBack={() => setCurrentStep("review")}
          isImporting={createTaskMutation.isPending}
        />
      )}
    </div>
  )
}
