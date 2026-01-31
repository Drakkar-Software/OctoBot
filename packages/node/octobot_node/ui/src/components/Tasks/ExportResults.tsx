import { useQuery } from "@tanstack/react-query"
import { Download } from "lucide-react"
import { useState } from "react"

import { type Task, TasksService } from "@/client"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { generateCSV, downloadCSV } from "@/lib/csv"

const ExportResults = () => {
  const [isExporting, setIsExporting] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data: tasks } = useQuery({
    queryFn: () => TasksService.getTasks({ page: 1, limit: 100 }),
    queryKey: ["tasks"],
  })

  const handleExport = async () => {
    if (!tasks || tasks.length === 0) {
      showErrorToast("No tasks available to export")
      return
    }

    setIsExporting(true)

    try {
      // Filter tasks that have results
      const tasksWithResults = tasks.filter(
        (task: Task) => task.result && task.result.trim() !== ""
      )

      if (tasksWithResults.length === 0) {
        showErrorToast("No tasks with results found to export")
        setIsExporting(false)
        return
      }

      const headers = ["name", "status", "result", "result_metadata"]
      const rows: unknown[][] = []
      
      for (const task of tasksWithResults) {
        let resultValue = task.result
        try {
          // Try to parse and stringify to format nicely
          const parsed = task.result ? JSON.parse(task.result) : null
          resultValue = parsed !== null ? JSON.stringify(parsed) : task.result
        } catch {
          // If parsing fails, use raw string
          resultValue = task.result
        }
        
        const row = [
          task.name || "",
          task.status || "",
          resultValue || "No result found",
          task.result_metadata
        ]
        
        rows.push(row)
      }

      // Generate and download CSV
      const csvString = generateCSV(headers, rows)
      const filename = `task-results-${new Date().toISOString().split("T")[0]}`
      downloadCSV(csvString, filename)

      showSuccessToast(
        `Exported ${tasksWithResults.length} task result${tasksWithResults.length > 1 ? "s" : ""}`
      )
    } catch (error) {
      showErrorToast(
        error instanceof Error ? error.message : "Failed to export results"
      )
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <Button
      variant="outline"
      className="my-4"
      onClick={handleExport}
      disabled={isExporting}
    >
      <Download className="h-4 w-4" />
      {isExporting ? "Exporting..." : "Export Results"}
    </Button>
  )
}

export default ExportResults

