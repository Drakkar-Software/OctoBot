import { createFileRoute } from "@tanstack/react-router"
import { Upload } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"

export const Route = createFileRoute("/_layout/octobots/import")({
  component: ImportOctobots,
  head: () => ({
    meta: [{ title: "Import OctoBots" }],
  }),
})

function ImportOctobots() {
  const [fileName, setFileName] = useState("")

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Import OctoBots</h1>
        <p className="text-muted-foreground">
          Upload a CSV or JSON file to restore OctoBots.
        </p>
      </div>
      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="size-4" />
              Upload file
            </CardTitle>
            <CardDescription>Accepted formats: `.csv` or `.json`.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <Input
              type="file"
              accept=".csv,application/json"
              onChange={(event) => {
                const file = event.target.files?.[0]
                setFileName(file?.name || "")
              }}
            />
            <div className="text-sm text-muted-foreground">
              {fileName ? `Selected: ${fileName}` : "No file selected."}
            </div>
            <Button>Import OctoBots</Button>
          </CardContent>
        </Card>
        <Card className="bg-muted/40">
          <CardHeader>
            <CardTitle>Import instructions</CardTitle>
            <CardDescription>Make sure your file follows the format.</CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <div>CSV should include at least: `name`, `type`, `status`.</div>
            <div>JSON should be an array of OctoBot objects.</div>
            <div>Any missing fields will be filled with defaults.</div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
