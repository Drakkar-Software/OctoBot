import { createFileRoute, useNavigate } from "@tanstack/react-router"

import ImportTask from "@/components/Tasks/ImportTask"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export const Route = createFileRoute("/_layout/octobots/import")({
  component: ImportOctobots,
  head: () => ({
    meta: [{ title: "Import OctoBots" }],
  }),
})

function ImportOctobots() {
  const navigate = useNavigate()

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Import OctoBots</h1>
        <p className="text-muted-foreground">
          Upload any CSV file. Columns will be auto-detected and mapped to action parameters.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Smart CSV Import</CardTitle>
          <CardDescription>
            Upload a CSV with any column format. The system will detect addresses, amounts, symbols,
            and other parameters automatically, then let you review and adjust before importing.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ImportTask onSuccess={() => navigate({ to: "/octobots" })} />
        </CardContent>
      </Card>
    </div>
  )
}
