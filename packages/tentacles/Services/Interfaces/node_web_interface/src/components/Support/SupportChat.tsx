import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Bug, Paperclip, Send, X } from "lucide-react"
import { useRef, useState } from "react"

import { DebugService } from "@/client"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { debugStateToFile } from "@/lib/debug/import"
import {
  closeTicket,
  fetchAttachment,
  getThread,
  sendAttachment,
  sendMessage,
  SUPPORT_TICKET_QUERY_KEY,
  type TicketMessage,
} from "@/lib/octochat"

function threadKey(nodeId: string) {
  return ["support-thread", nodeId] as const
}

export function SupportChat({
  nodeId,
  title,
}: {
  nodeId: string
  title: string
}) {
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const [draft, setDraft] = useState("")
  const fileInput = useRef<HTMLInputElement>(null)

  const { data: messages = [], isLoading } = useQuery({
    queryKey: threadKey(nodeId),
    queryFn: () => getThread(nodeId),
    refetchInterval: 8_000,
  })

  const refresh = () =>
    queryClient.invalidateQueries({ queryKey: threadKey(nodeId) })

  const sendMutation = useMutation({
    mutationFn: (text: string) => sendMessage(nodeId, text),
    onSuccess: () => {
      setDraft("")
      refresh()
    },
    onError: () => showErrorToast("Message not sent — try again"),
  })

  const attachMutation = useMutation({
    mutationFn: (file: File) =>
      file.arrayBuffer().then((buf) =>
        sendAttachment(nodeId, {
          bytes: new Uint8Array(buf),
          name: file.name,
          mime: file.type || "application/octet-stream",
        }),
      ),
    onSuccess: refresh,
    onError: () => showErrorToast("Attachment not sent — try again"),
  })

  const debugMutation = useMutation({
    mutationFn: async () => {
      const state = await DebugService.getDebug({})
      const wallet = localStorage.getItem("auth_username") ?? ""
      const file = debugStateToFile(state, wallet)
      await sendAttachment(nodeId, file, "Shared a debug snapshot")
    },
    onSuccess: () => {
      showSuccessToast("Debug snapshot shared")
      refresh()
    },
    onError: () => showErrorToast("Couldn't share the debug snapshot"),
  })

  const closeMutation = useMutation({
    mutationFn: () => closeTicket(nodeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SUPPORT_TICKET_QUERY_KEY })
    },
    onError: () => showErrorToast("Couldn't close the ticket"),
  })

  const busy =
    sendMutation.isPending ||
    attachMutation.isPending ||
    debugMutation.isPending

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold tracking-tight">
            {title.trim() || "Support ticket"}
          </h1>
          <p className="text-sm text-muted-foreground">
            A private chat with the OctoBot team. Replies appear here.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={busy || closeMutation.isPending}
          onClick={() => closeMutation.mutate()}
        >
          <X className="size-3.5" />
          Close ticket
        </Button>
      </div>

      <div className="flex flex-1 flex-col gap-3 overflow-y-auto rounded-card border border-rule bg-surface-soft p-4">
        {isLoading && (
          <span className="text-sm text-muted-foreground">Loading…</span>
        )}
        {!isLoading && messages.length === 0 && (
          <span className="text-sm text-muted-foreground">
            No messages yet. Say hello, attach a file, or share a debug snapshot
            to get started.
          </span>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} nodeId={nodeId} />
        ))}
      </div>

      <div className="flex flex-col gap-2">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (
              e.key === "Enter" &&
              (e.metaKey || e.ctrlKey) &&
              !busy &&
              draft.trim()
            ) {
              sendMutation.mutate(draft.trim())
            }
          }}
          placeholder="Write a message…  (⌘/Ctrl+Enter to send)"
          rows={3}
          className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
        <div className="flex flex-wrap items-center gap-2">
          <input
            ref={fileInput}
            type="file"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) attachMutation.mutate(file)
              e.target.value = ""
            }}
          />
          <Button
            variant="outline"
            size="sm"
            disabled={busy}
            onClick={() => fileInput.current?.click()}
          >
            <Paperclip className="size-3.5" />
            Attach file
          </Button>
          <LoadingButton
            variant="outline"
            size="sm"
            loading={debugMutation.isPending}
            disabled={busy}
            onClick={() => debugMutation.mutate()}
          >
            <Bug className="size-3.5" />
            Share debug state
          </LoadingButton>
          <LoadingButton
            className="ml-auto"
            size="sm"
            loading={sendMutation.isPending}
            disabled={busy || draft.trim().length === 0}
            onClick={() => sendMutation.mutate(draft.trim())}
          >
            <Send className="size-3.5" />
            Send
          </LoadingButton>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({
  message,
  nodeId,
}: {
  message: TicketMessage
  nodeId: string
}) {
  const { showErrorToast } = useCustomToast()
  const [downloading, setDownloading] = useState(false)

  const download = async () => {
    if (!message.attachment) return
    setDownloading(true)
    try {
      const bytes = await fetchAttachment(nodeId, message.attachment)
      const blob = new Blob([bytes as unknown as BlobPart], {
        type: message.attachment.mime || "application/octet-stream",
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = message.attachment.name || "attachment"
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } catch {
      showErrorToast("Couldn't download the attachment")
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div
      className={`flex flex-col ${message.fromMe ? "items-end" : "items-start"}`}
    >
      <div
        className={`max-w-[80%] rounded-card px-3 py-2 text-sm ${
          message.fromMe
            ? "bg-primary text-primary-foreground"
            : "bg-surface border border-rule"
        }`}
      >
        {message.text && (
          <span className="whitespace-pre-wrap break-words">
            {message.text}
          </span>
        )}
        {message.attachment && (
          <button
            type="button"
            onClick={download}
            disabled={downloading}
            className="mt-1 flex items-center gap-1.5 text-xs underline underline-offset-2 disabled:opacity-60"
          >
            <Paperclip className="size-3" />
            {downloading ? "Downloading…" : message.attachment.name}
          </button>
        )}
      </div>
    </div>
  )
}
