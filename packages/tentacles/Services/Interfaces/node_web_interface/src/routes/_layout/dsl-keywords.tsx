import { createFileRoute } from "@tanstack/react-router"

import { DslKeywordsView } from "@/components/DslKeywords/DslKeywordsView"

function DslKeywordsPage() {
  return <DslKeywordsView />
}

export const Route = createFileRoute("/_layout/dsl-keywords")({
  component: DslKeywordsPage,
  head: () => ({
    meta: [{ title: "DSL keywords" }],
  }),
})
