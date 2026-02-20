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
          Upload a CSV file to restore OctoBots.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Upload file</CardTitle>
          <CardDescription>Accepted format: `.csv`.</CardDescription>
        </CardHeader>
        <CardContent>
          <ImportTask onSuccess={() => navigate({ to: "/octobots" })} />
        </CardContent>
      </Card>
    </div>
  )
}
