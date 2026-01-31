import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Upload, FileText } from "lucide-react"
import { useRef, useState } from "react"

import { type Task, TasksService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { parseCSVFile, type CSVRow } from "@/lib/csv"
import { handleError } from "@/utils"

const ImportTask = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [parsedTasks, setParsedTasks] = useState<CSVRow[]>([])
  const [isParsing, setIsParsing] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const createTaskMutation = useMutation({
    mutationFn: (data: Array<Task>) =>
      TasksService.createTasks({ requestBody: data }),
    onError: handleError.bind(showErrorToast),
  })

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setSelectedFile(file)
    setIsParsing(true)

    try {
      const tasks: Array<CSVRow> = await parseCSVFile(file)
      if (tasks.length === 0) {
        showErrorToast("No valid tasks found in the CSV file")
        setSelectedFile(null)
        setIsParsing(false)
        return
      }

      setParsedTasks(tasks)
    } catch (error) {
      showErrorToast(
        error instanceof Error ? error.message : "Failed to parse CSV file"
      )
      setSelectedFile(null)
      setParsedTasks([])
    } finally {
      setIsParsing(false)
    }
  }

  const handleImport = async () => {
    if (parsedTasks.length === 0) {
      showErrorToast("No tasks to import")
      return
    }

    try {
      const tasks = parsedTasks.map(task => ({
        name: task.name,
        content: task.content,
        type: task.type,
        content_metadata: task.metadata,
      } as Task))

      const [successCount, errorCount] = await createTaskMutation.mutateAsync(tasks)

      if (successCount > 0) {
        showSuccessToast(
          `Successfully imported task${successCount > 1 ? "s" : ""}${
            errorCount > 0 ? ` (${errorCount} failed)` : ""
          }`
        )
      } else {
        showErrorToast("Failed to import tasks")
      }

      // Reset state
      setSelectedFile(null)
      setParsedTasks([])
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
      setIsOpen(false)

      // Invalidate queries to refresh the task list
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
    } catch (error) {
      showErrorToast("An error occurred during import")
    }
  }

  const handleDialogClose = (open: boolean) => {
    setIsOpen(open)
    if (!open) {
      // Reset state when dialog closes
      setSelectedFile(null)
      setParsedTasks([])
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
    }
  }

  const isImporting = createTaskMutation.isPending

  return (
    <Dialog open={isOpen} onOpenChange={handleDialogClose}>
      <DialogTrigger asChild>
        <Button variant="outline" className="my-4">
          <Upload className="h-4 w-4" />
          Import Tasks
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Import Tasks from CSV</DialogTitle>
          <DialogDescription>
            Upload a CSV file to import multiple tasks at once. The file must contain "name" and "type" columns, and optionally a "content" column.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 py-4">
          <div className="flex flex-col gap-2">
            <label
              htmlFor="csv-file"
              className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-border rounded-lg cursor-pointer hover:bg-muted/50 transition-colors"
            >
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                {selectedFile ? (
                  <>
                    <FileText className="w-10 h-10 mb-2 text-muted-foreground" />
                    <p className="mb-1 text-sm font-medium text-foreground">
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {parsedTasks.length > 0
                        ? `${parsedTasks.length} task${parsedTasks.length > 1 ? "s" : ""} found`
                        : "Processing..."}
                    </p>
                  </>
                ) : (
                  <>
                    <Upload className="w-10 h-10 mb-2 text-muted-foreground" />
                    <p className="mb-1 text-sm font-medium text-foreground">
                      Click to upload or drag and drop
                    </p>
                    <p className="text-xs text-muted-foreground">CSV file only</p>
                  </>
                )}
              </div>
              <input
                ref={fileInputRef}
                id="csv-file"
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleFileSelect}
                disabled={isParsing || isImporting}
              />
            </label>
          </div>

          {parsedTasks.length > 0 && (
            <div className="rounded-md border border-border bg-muted/30 p-3">
              <p className="text-sm font-medium mb-2">Preview ({parsedTasks.length} tasks):</p>
              <div className="max-h-32 overflow-y-auto space-y-1">
                {parsedTasks.slice(0, 5).map((task, index) => (
                  <div key={index} className="text-xs text-muted-foreground">
                    <span className="font-medium">{task.name}</span>
                    <span className="ml-2 text-muted-foreground/70">({task.type})</span>
                  </div>
                ))}
                {parsedTasks.length > 5 && (
                  <p className="text-xs text-muted-foreground italic">
                    ... and {parsedTasks.length - 5} more
                  </p>
                )}
              </div>
            </div>
          )}

          <div className="rounded-md border border-border bg-muted/30 p-3">
            <p className="text-xs text-muted-foreground">
              <strong>CSV Format:</strong> The first row must be a header row with "name" and "type" columns (required), and optionally a "content" column. Additional columns will be included in the content field.
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Example: <code className="bg-background px-1 rounded">name,content,type</code> or <code className="bg-background px-1 rounded">"Task 1","JSON content","execute_actions"</code>
            </p>
          </div>
        </div>

        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline" disabled={isImporting || isParsing}>
              Cancel
            </Button>
          </DialogClose>
          <LoadingButton
            onClick={handleImport}
            loading={isImporting}
            disabled={parsedTasks.length === 0 || isParsing}
          >
            Import {parsedTasks.length > 0 ? `${parsedTasks.length} ` : ""}Task
            {parsedTasks.length > 1 ? "s" : ""}
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default ImportTask

