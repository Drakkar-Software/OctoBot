import { useQuery } from "@tanstack/react-query"
import { BookOpen } from "lucide-react"
import { useEffect } from "react"

import { type ApiError, DslService } from "@/client"
import { DslKeywordsTable } from "@/components/DslKeywords/DslKeywordsTable"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

export function DslKeywordsView() {
  const { showErrorToast } = useCustomToast()

  const keywordsQuery = useQuery({
    queryKey: ["dsl-keywords"],
    queryFn: () => DslService.getDslKeywords(),
  })

  useEffect(() => {
    if (keywordsQuery.isError && keywordsQuery.error) {
      handleError.bind(showErrorToast)(keywordsQuery.error as ApiError)
    }
  }, [keywordsQuery.isError, keywordsQuery.error, showErrorToast])

  const keywords = keywordsQuery.data?.keywords ?? []
  const version = keywordsQuery.data?.version

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start gap-3">
        <BookOpen className="mt-1 size-6 text-muted-foreground" />
        <div>
          <h1 className="text-2xl font-bold tracking-tight">DSL keywords</h1>
          <p className="text-sm text-muted-foreground">
            Keywords available on this node
            {version ? (
              <>
                {" "}
                · catalog version <span className="font-mono">{version}</span>
              </>
            ) : null}
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Catalog</CardTitle>
          <CardDescription>
            Search and sort the full DSL operator catalog. Open a row for the
            complete keyword JSON.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {keywordsQuery.isPending ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              Loading keywords…
            </p>
          ) : keywordsQuery.isError ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              Could not load DSL keywords.
            </p>
          ) : (
            <DslKeywordsTable rows={keywords} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
