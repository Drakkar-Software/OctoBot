import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { BookOpen, Bug, ExternalLink, LifeBuoy } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import {
  createSupportTicket,
  getSupportTicket,
  SUPPORT_TICKET_QUERY_KEY,
} from "@/lib/octochat"

export function SupportCard() {
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState("")
  const [message, setMessage] = useState("")

  const { data: ticket, isLoading } = useQuery({
    queryKey: SUPPORT_TICKET_QUERY_KEY,
    queryFn: getSupportTicket,
    refetchInterval: (query) => {
      const s = query.state.data?.status
      return s === "pending" ? 10_000 : false
    },
  })

  const createMutation = useMutation({
    mutationFn: () =>
      createSupportTicket({ title: title.trim(), message: message.trim() }),
    onSuccess: () => {
      setOpen(false)
      setTitle("")
      setMessage("")
      queryClient.invalidateQueries({ queryKey: SUPPORT_TICKET_QUERY_KEY })
    },
    onError: (err) =>
      showErrorToast(
        err instanceof Error ? err.message : "Couldn't open the ticket",
      ),
  })

  const status = ticket?.status ?? (isLoading ? "loading" : "none")

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <LifeBuoy className="size-4" />
          Help
        </CardTitle>
        <CardDescription>
          Get help from the OctoBot team or browse the docs.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col items-start gap-3">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Guides
          </span>
          <span className="text-sm text-muted-foreground">
            Setup walkthroughs and how-tos for running OctoBot.
          </span>
          <Button variant="outline" size="sm" asChild>
            <a
              href="https://www.octobot.cloud/en/guides/octobot"
              target="_blank"
              rel="noopener noreferrer"
            >
              <BookOpen className="size-4" />
              Browse guides
              <ExternalLink className="size-3.5" />
            </a>
          </Button>
        </div>
        <div className="border-t" />
        <div className="flex flex-col items-start gap-3">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Support
          </span>
          {status === "loading" && (
            <span className="text-xs text-muted-foreground">Loading…</span>
          )}

          {status === "disabled" && (
            <span className="text-xs text-muted-foreground">
              Support isn't available on this OctoBot.
            </span>
          )}

          {status === "none" && (
            <>
              <span className="text-sm text-muted-foreground">
                Stuck on something? Leave a message and the team will get back to
                you. Share a debug snapshot in one click.
              </span>
              <Button size="sm" onClick={() => setOpen(true)}>
                New ticket
              </Button>
            </>
          )}

          {status === "pending" && (
            <>
              <span className="text-sm text-muted-foreground">
                The DRAKKAR-SOFTWARE team hasn't accepted your ticket yet. Replies
                will appear here once they do. You can share logs after that.
              </span>
              <Button variant="outline" size="sm" asChild>
                <Link to="/support">View status</Link>
              </Button>
            </>
          )}

          {ticket?.status === "resolved" && (
            <>
              <span className="text-sm text-muted-foreground">
                Your previous ticket was resolved. Open a new one any time.
              </span>
              <div className="flex items-center gap-2">
                <Button size="sm" onClick={() => setOpen(true)}>
                  New ticket
                </Button>
                <Button variant="outline" size="sm" asChild>
                  <Link to="/support">View</Link>
                </Button>
              </div>
            </>
          )}

          {ticket?.status === "open" && (
            <>
              <span className="text-sm">
                {ticket.allTickets.length > 1
                  ? `${ticket.allTickets.length} open tickets`
                  : (ticket.title?.trim() || "Support ticket")}
              </span>
              <Button variant="outline" size="sm" asChild>
                <Link to="/support">
                  {ticket.allTickets.length > 1 ? "View tickets" : "Open ticket"}
                </Link>
              </Button>
            </>
          )}
        </div>
        <div className="border-t" />
        <div className="flex flex-col items-start gap-3">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Developer
          </span>
          <span className="text-sm text-muted-foreground">
            Inspect runtime state, download logs, and run debug actions.
          </span>
          <Button variant="outline" size="sm" asChild>
            <Link to="/debug">
              <Bug className="size-4" />
              Developer view
            </Link>
          </Button>
        </div>
      </CardContent>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New support ticket</DialogTitle>
            <DialogDescription>
              Tell us what's going on. The team will get back to you, this is not a live chat.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="support-title">Subject</Label>
              <Input
                id="support-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Short summary"
                maxLength={200}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="support-message">Message</Label>
              <textarea
                id="support-message"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="What happened, and what were you trying to do?"
                rows={4}
                className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline" disabled={createMutation.isPending}>
                Cancel
              </Button>
            </DialogClose>
            <LoadingButton
              loading={createMutation.isPending}
              disabled={
                title.trim().length === 0 || message.trim().length === 0
              }
              onClick={() => createMutation.mutate()}
            >
              Open ticket
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
