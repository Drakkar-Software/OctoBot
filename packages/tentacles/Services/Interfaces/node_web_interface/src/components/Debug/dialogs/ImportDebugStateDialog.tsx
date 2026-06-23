import { Upload } from "lucide-react"
import {
  type ChangeEvent,
  type ClipboardEvent,
  useEffect,
  useRef,
  useState,
} from "react"
import { toast } from "sonner"

import type { DebugState } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LineNumberTextarea } from "@/components/ui/line-number-textarea"
import { parseDebugStateJson } from "@/lib/debug/import"

type ImportDebugStateDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  onImported: (state: DebugState, sourceLabel: string) => void
}

export function ImportDebugStateDialog({
  open,
  onOpenChange,
  onImported,
}: ImportDebugStateDialogProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [jsonText, setJsonText] = useState("")
  const [parseError, setParseError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setJsonText("")
      setParseError(null)
    }
  }, [open])

  const tryImportSnapshot = (text: string, sourceLabel: string): boolean => {
    const result = parseDebugStateJson(text)
    if ("error" in result) {
      setParseError(result.error)
      return false
    }
    onImported(result.state, sourceLabel)
    onOpenChange(false)
    toast.success("Debug snapshot imported")
    return true
  }

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    setParseError(null)
    const reader = new FileReader()
    reader.onload = () => {
      const text = typeof reader.result === "string" ? reader.result : ""
      tryImportSnapshot(text, file.name)
    }
    reader.readAsText(file)
    event.target.value = ""
  }

  const handleImport = () => {
    tryImportSnapshot(jsonText, "Pasted JSON")
  }

  const handleJsonPaste = (event: ClipboardEvent<HTMLTextAreaElement>) => {
    const pastedText = event.clipboardData.getData("text")
    if (!pastedText.trim()) return
    const result = parseDebugStateJson(pastedText)
    if ("state" in result) {
      event.preventDefault()
      tryImportSnapshot(pastedText, "Pasted JSON")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Import debug snapshot</DialogTitle>
          <DialogDescription>
            Choose a .json file to load immediately, or paste JSON below.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4 min-h-0 flex-1">
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,application/json"
            className="hidden"
            onChange={handleFileChange}
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="w-fit"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="size-4" />
            Choose file
          </Button>
          <LineNumberTextarea
            className="min-h-[240px] flex-1"
            textareaClassName="min-h-[240px]"
            value={jsonText}
            onPaste={handleJsonPaste}
            onChange={(event) => {
              setJsonText(event.target.value)
              if (parseError) setParseError(null)
            }}
          />
          {parseError && (
            <p className="text-sm text-destructive">{parseError}</p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleImport}>Import</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
