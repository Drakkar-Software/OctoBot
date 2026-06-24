import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { ChevronLeft, ChevronRight, LifeBuoy } from "lucide-react"
import { useState } from "react"

import { SupportChat } from "@/components/Support/SupportChat"
import { Button } from "@/components/ui/button"
import { cancelPendingTicket, getSupportTicket, SUPPORT_TICKET_QUERY_KEY } from "@/lib/octochat"

function EmptyState({
  title,
  body,
  action,
}: {
  title: string
  body: string
  action?: React.ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-card border border-rule bg-surface-soft px-6 py-16 text-center">
      <LifeBuoy className="size-8 text-muted-foreground" />
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="max-w-sm text-sm text-muted-foreground">{body}</p>
      {action}
    </div>
  )
}

function TicketSelector({
  tickets,
  onSelect,
}: {
  tickets: Array<{ nodeId: string; title: string }>
  onSelect: (nodeId: string) => void
}) {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold tracking-tight">Open tickets</h1>
      <div className="flex flex-col gap-2">
        {tickets.map((t) => (
          <button
            key={t.nodeId}
            type="button"
            onClick={() => onSelect(t.nodeId)}
            className="flex items-center justify-between rounded-card border border-rule bg-surface-soft px-4 py-3 text-left text-sm hover:bg-surface"
          >
            <span className="font-medium">{t.title.trim() || "Support ticket"}</span>
            <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
          </button>
        ))}
      </div>
    </div>
  )
}

function SupportPage() {
  const queryClient = useQueryClient()
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const { data: ticket, isLoading } = useQuery({
    queryKey: SUPPORT_TICKET_QUERY_KEY,
    queryFn: getSupportTicket,
    refetchInterval: (query) => {
      const s = query.state.data?.status
      return s === "pending" ? 10_000 : false
    },
  })

  const cancelMutation = useMutation({
    mutationFn: cancelPendingTicket,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SUPPORT_TICKET_QUERY_KEY }),
  })

  if (isLoading) {
    return <span className="text-sm text-muted-foreground">Loading…</span>
  }

  if (!ticket || ticket.status === "disabled") {
    return (
      <EmptyState
        title="Support unavailable"
        body="This OctoBot isn't configured to reach the support desk."
      />
    )
  }

  if (ticket.status === "none") {
    return (
      <EmptyState
        title="No ticket yet"
        body="Open a ticket from Settings to leave a secure message for the team."
        action={
          <Button asChild>
            <Link to="/settings">Go to Settings</Link>
          </Button>
        }
      />
    )
  }

  if (ticket.status === "pending") {
    return (
      <EmptyState
        title="Waiting for the team"
        body="Your request has been delivered. The team will get back to you, it may take some time."
        action={
          <Button
            variant="ghost"
            size="sm"
            onClick={() => cancelMutation.mutate()}
            disabled={cancelMutation.isPending}
          >
            Cancel request
          </Button>
        }
      />
    )
  }

  if (ticket.status !== "open") return null

  const { allTickets } = ticket

  if (allTickets.length > 1 && selectedNodeId === null) {
    return <TicketSelector tickets={allTickets} onSelect={setSelectedNodeId} />
  }

  const activeId = (selectedNodeId !== null && allTickets.some((t) => t.nodeId === selectedNodeId)) ? selectedNodeId : ticket.nodeId
  const activeTitle = allTickets.find((t) => t.nodeId === activeId)?.title ?? ticket.title

  return (
    <div className="flex h-[calc(100vh-9rem)] flex-col">
      {allTickets.length > 1 && (
        <div className="shrink-0 pb-2">
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5"
            onClick={() => setSelectedNodeId(null)}
          >
            <ChevronLeft className="size-4" />
            All tickets
          </Button>
        </div>
      )}
      <div className="min-h-0 flex-1">
        <SupportChat nodeId={activeId} title={activeTitle} />
      </div>
    </div>
  )
}

export const Route = createFileRoute("/_layout/support")({
  component: SupportPage,
  head: () => ({
    meta: [{ title: "Support" }],
  }),
})
