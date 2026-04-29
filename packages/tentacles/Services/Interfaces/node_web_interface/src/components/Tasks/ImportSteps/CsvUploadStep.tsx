import { Upload, FileText } from "lucide-react"
import { useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import useCustomToast from "@/hooks/useCustomToast"
import { parseCSVRaw, isValidCSVFile, type CSVRawResult } from "@/lib/csv"

export interface CsvUploadStepProps {
  onParsed: (result: CSVRawResult) => void
}

const MAX_PREVIEW_ROWS = 5
const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10 MB
const MAX_IMPORT_ROWS = 500

export default function CsvUploadStep({ onParsed }: CsvUploadStepProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<CSVRawResult | null>(null)
  const [isParsing, setIsParsing] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { showErrorToast } = useCustomToast()

  const handleFileSelect = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0]
    if (!file) return

    if (!isValidCSVFile(file)) {
      showErrorToast("File must be a CSV file")
      return
    }

    if (file.size > MAX_FILE_SIZE) {
      showErrorToast("File too large (max 10 MB)")
      return
    }

    setSelectedFile(file)
    setIsParsing(true)

    try {
      const text = await file.text()
      const result = parseCSVRaw(text)
      if (result.rows.length === 0) {
        showErrorToast("No data rows found in the CSV file")
        setSelectedFile(null)
        setIsParsing(false)
        return
      }
      if (result.rows.length > MAX_IMPORT_ROWS) {
        result.rows = result.rows.slice(0, MAX_IMPORT_ROWS)
        showErrorToast(
          `CSV has more than ${MAX_IMPORT_ROWS} rows. Only the first ${MAX_IMPORT_ROWS} will be imported.`,
        )
      }
      setPreview(result)
    } catch (error) {
      showErrorToast(
        error instanceof Error ? error.message : "Failed to parse CSV file",
      )
      setSelectedFile(null)
      setPreview(null)
    } finally {
      setIsParsing(false)
    }
  }

  const reset = () => {
    setSelectedFile(null)
    setPreview(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <label
        htmlFor="csv-file-upload"
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
                {preview
                  ? `${preview.headers.length} columns, ${preview.rows.length} row${preview.rows.length > 1 ? "s" : ""}`
                  : "Processing..."}
              </p>
            </>
          ) : (
            <>
              <Upload className="w-10 h-10 mb-2 text-muted-foreground" />
              <p className="mb-1 text-sm font-medium text-foreground">
                Click to upload
              </p>
              <p className="text-xs text-muted-foreground">
                CSV file with any column format
              </p>
            </>
          )}
        </div>
        <input
          ref={fileInputRef}
          id="csv-file-upload"
          type="file"
          accept=".csv"
          className="hidden"
          onChange={handleFileSelect}
          disabled={isParsing}
        />
      </label>

      {preview && (
        <>
          <div className="rounded-md border border-border bg-muted/30 p-3">
            <p className="text-sm font-medium mb-2">
              Preview (first {Math.min(MAX_PREVIEW_ROWS, preview.rows.length)} of{" "}
              {preview.rows.length} rows):
            </p>
            <div className="max-h-64 overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    {preview.headers.map((header, i) => (
                      <TableHead key={i}>{header}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.rows.slice(0, MAX_PREVIEW_ROWS).map((row, rowIdx) => (
                    <TableRow key={rowIdx}>
                      {preview.headers.map((_, colIdx) => (
                        <TableCell key={colIdx} className="max-w-[200px] truncate">
                          {row[colIdx] ?? ""}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>

          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={reset}>
              Reset
            </Button>
            <Button onClick={() => onParsed(preview)}>
              Continue to Mapping
            </Button>
          </div>
        </>
      )}
    </div>
  )
}
