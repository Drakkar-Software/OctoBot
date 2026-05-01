import { createFileRoute, useNavigate } from "@tanstack/react-router"

import ImportTask from "@/components/Tasks/ImportTask"

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
          Upload any CSV file. Columns will be auto-detected and mapped to
          action parameters.
        </p>
      </div>
      <ImportTask onSuccess={() => navigate({ to: "/octobots" })} />
    </div>
  )
}
