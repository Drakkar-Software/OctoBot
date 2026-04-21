import { createFileRoute } from "@tanstack/react-router"
import { Check, Copy, Download, FileText, KeyRound, Network, QrCode, Server, ShieldCheck, Sliders, TriangleAlert, Wallet, X } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import QRCode from "react-qr-code"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import useAuth from "@/hooks/useAuth"
import {
  CLIENT_KEY_LABELS,
  CLIENT_KEY_NAMES,
  areClientKeysConfigured,
  emptyKeys,
} from "@/lib/client-encryption"
import type { ClientKeys } from "@/lib/client-encryption"
import {
  clearClientKeys,
  hasStoredClientKeys,
  loadClientKeys,
  loadPassword,
  saveClientKeys,
} from "@/lib/device-key"

export const Route = createFileRoute("/_layout/settings")({
  component: Settings,
  head: () => ({
    meta: [{ title: "Settings" }],
  }),
})

function StatusIndicator({ enabled }: { enabled: boolean | null }) {
  if (enabled === null) return null
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        {enabled ? (
          <span className="flex size-6 items-center justify-center rounded-full bg-foreground text-background">
            <Check className="size-3.5" strokeWidth={3} />
          </span>
        ) : (
          <span className="flex size-6 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <X className="size-3.5" strokeWidth={3} />
          </span>
        )}
      </TooltipTrigger>
      <TooltipContent side="left">
        {enabled ? "Enabled" : "Disabled"}
      </TooltipContent>
    </Tooltip>
  )
}

function LoggingCard() {
  const [enabled, setEnabled] = useState<boolean | null>(null)

  useEffect(() => {
    fetch("/api/v1/nodes/config", { credentials: "include" })
      .then((r) => r.json())
      .then((data) => setEnabled(data.use_dedicated_log_file_per_automation ?? true))
      .catch(() => setEnabled(true))
  }, [])

  return (
    <Card className="relative">
      <div className="absolute right-4 top-4">
        <StatusIndicator enabled={enabled} />
      </div>
      <CardHeader className="pr-12">
        <CardTitle className="flex items-center gap-2">
          <FileText className="size-4" />
          Logging
        </CardTitle>
        <CardDescription>
          Per-bot log files and diagnostic settings.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <span className="text-xs text-muted-foreground">
          {enabled === null
            ? "Loading…"
            : enabled
              ? "A dedicated log file is written for each bot run."
              : "Bot logs are written to the main log file."}
        </span>
        <span className="text-xs text-muted-foreground">
          Configure via <code>USE_DEDICATED_LOG_FILE_PER_AUTOMATION</code>.
        </span>
      </CardContent>
    </Card>
  )
}

async function buildAuthHeader() {
  const username = localStorage.getItem("auth_username") || "node"
  const password = (await loadPassword()) ?? ""
  return `Basic ${btoa(`${username}:${password}`)}`
}

function ExportWalletDialog() {
  const [privateKey, setPrivateKey] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const fetchPrivateKey = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch("/api/v1/setup/wallet/export", {
        headers: { Authorization: await buildAuthHeader() },
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setPrivateKey(data.private_key)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to export wallet")
    } finally {
      setLoading(false)
    }
  }

  const copy = () => {
    if (!privateKey) return
    navigator.clipboard.writeText(privateKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const onOpenChange = (open: boolean) => {
    if (!open) { setPrivateKey(null); setError(null) }
  }

  return (
    <Dialog onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <button
          className="inline-flex w-fit items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-accent"
          onClick={fetchPrivateKey}
        >
          <Download className="size-4" />
          Export wallet
        </button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Export wallet</DialogTitle>
          <DialogDescription>
            Keep your private key safe. Anyone with access to it controls your wallet.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex items-start gap-2 rounded-md border border-yellow-500/40 bg-yellow-500/10 p-3 text-sm text-yellow-600 dark:text-yellow-400">
            <TriangleAlert className="mt-0.5 size-4 shrink-0" />
            <span>Never share your private key. Store it in a secure location.</span>
          </div>
          {loading && <p className="text-sm text-muted-foreground">Decrypting wallet…</p>}
          {error && <p className="text-sm text-destructive">{error}</p>}
          {privateKey && (
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between rounded-md border bg-muted px-3 py-2">
                <code className="text-xs break-all">{privateKey}</code>
                <button
                  className="ml-3 shrink-0 text-muted-foreground hover:text-foreground"
                  onClick={copy}
                  title="Copy"
                >
                  <Copy className="size-4" />
                </button>
              </div>
              {copied && <p className="text-xs text-muted-foreground">Copied!</p>}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function PairDeviceDialog() {
  const [qrValue, setQrValue] = useState<string | null>(null)

  const onOpenChange = async (open: boolean) => {
    if (open) {
      const address = localStorage.getItem("auth_username") || ""
      const passphrase = (await loadPassword()) ?? ""
      setQrValue(JSON.stringify({
        url: window.location.origin,
        address,
        passphrase,
      }))
    } else {
      setQrValue(null)
    }
  }

  return (
    <Dialog onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <button className="inline-flex w-fit items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-accent">
          <QrCode className="size-4" />
          Pair device
        </button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Pair mobile device</DialogTitle>
          <DialogDescription>
            Scan this QR code with your OctoBot mobile app to connect to this node.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col items-center gap-4">
          <div className="flex items-start gap-2 rounded-md border border-yellow-500/40 bg-yellow-500/10 p-3 text-sm text-yellow-600 dark:text-yellow-400 w-full">
            <TriangleAlert className="mt-0.5 size-4 shrink-0" />
            <span>Only scan on a trusted device. The QR code contains your passphrase.</span>
          </div>
          {qrValue && (
            <div className="rounded-xl bg-white p-4">
              <QRCode value={qrValue} size={220} />
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function WalletCard() {
  const { user } = useAuth()

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Wallet className="size-4" />
          OctoBot wallet
        </CardTitle>
        <CardDescription>
          Your node's EVM identity address.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-sm text-muted-foreground font-mono truncate">
          {user?.email ?? "—"}
        </p>
        <div className="flex flex-wrap gap-2">
          <ExportWalletDialog />
          <PairDeviceDialog />
        </div>
      </CardContent>
    </Card>
  )
}

type NodeType = "standalone" | "master"

function NodeTypeCard() {
  const [nodeType, setNodeType] = useState<NodeType | null>(null)

  useEffect(() => {
    fetch("/api/v1/nodes/config", { credentials: "include" })
      .then((r) => r.json())
      .then((data) => setNodeType(data.node_type ?? "standalone"))
      .catch(() => setNodeType("standalone"))
  }, [])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sliders className="size-4" />
          Node type
        </CardTitle>
        <CardDescription>
          How this node is configured to run.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-3">
          <div
            className={`flex flex-col items-center gap-2 rounded-lg border p-4 text-sm ${
              nodeType === "standalone"
                ? "border-primary bg-primary/5 text-primary"
                : "text-muted-foreground"
            }`}
          >
            <Server className="size-6" />
            Standalone
          </div>
          <div className="relative flex flex-col items-center gap-2 rounded-lg border p-4 text-sm opacity-50 cursor-not-allowed text-muted-foreground">
            <Network className="size-6" />
            Master / Replica
            <span className="absolute -top-2 right-2 rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground border">
              Coming soon
            </span>
          </div>
        </div>
        <span className="text-xs text-muted-foreground">
          The node type can only be changed from the CLI. Use the <code>--node-type</code> flag when starting the node.
        </span>
      </CardContent>
    </Card>
  )
}

function EncryptionCard() {
  const [enabled, setEnabled] = useState<boolean | null>(null)
  const [envVars, setEnvVars] = useState<string[]>([])

  useEffect(() => {
    fetch("/api/v1/nodes/config", { credentials: "include" })
      .then((r) => r.json())
      .then((data) => {
        setEnabled(data.tasks_encryption_enabled ?? false)
        setEnvVars(data.server_encryption_env_vars ?? [])
      })
      .catch(() => setEnabled(false))
  }, [])

  return (
    <Card className="relative">
      <div className="absolute right-4 top-4">
        <StatusIndicator enabled={enabled} />
      </div>
      <CardHeader className="pr-12">
        <CardTitle className="flex items-center gap-2">
          <ShieldCheck className="size-4" />
          Task encryption
        </CardTitle>
        <CardDescription>
          Server-side encryption keys for task inputs.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {enabled === null ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : enabled ? (
          <span className="text-xs text-muted-foreground">
            All server encryption keys are configured.
          </span>
        ) : (
          <div className="flex flex-col gap-2">
            <span className="text-xs text-muted-foreground">
              Define the following environment variables to enable:
            </span>
            <ul className="text-xs font-mono text-muted-foreground flex flex-col gap-0.5 ml-6 list-disc">
              {envVars.map((v) => (
                <li key={v}>{v}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function ClientEncryptionKeysCard() {
  const [keys, setKeys] = useState<ClientKeys>(emptyKeys)
  const [status, setStatus] = useState<"loading" | "ready" | "saved" | "error">("loading")
  const [hasStored, setHasStored] = useState(false)
  const [editing, setEditing] = useState(false)
  const [error, setError] = useState("")
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const configured = areClientKeysConfigured(keys)

  useEffect(() => {
    ;(async () => {
      const stored = await hasStoredClientKeys()
      setHasStored(stored)
      if (!stored) {
        setStatus("ready")
        return
      }
      try {
        const loaded = await loadClientKeys()
        if (loaded) setKeys(loaded as ClientKeys)
        setStatus("ready")
      } catch {
        setStatus("error")
        setError("Failed to decrypt stored keys.")
      }
    })()
  }, [])

  const handleSave = async () => {
    try {
      await saveClientKeys(keys)
      setHasStored(true)
      setStatus("saved")
      setEditing(false)
      setError("")
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => setStatus("ready"), 2000)
    } catch (e) {
      setStatus("error")
      setError(e instanceof Error ? e.message : "Encryption failed")
    }
  }

  const handleClear = async () => {
    await clearClientKeys()
    setHasStored(false)
    setKeys(emptyKeys())
    setStatus("ready")
    setError("")
  }

  return (
    <Card className="relative md:col-span-2">
      <div className="absolute right-4 top-4">
        <StatusIndicator enabled={configured && hasStored} />
      </div>
      <CardHeader className="pr-12">
        <CardTitle className="flex items-center gap-2">
          <KeyRound className="size-4" />
          Client encryption keys
        </CardTitle>
        <CardDescription>
          Browser-stored user keys for encrypting tasks and decrypting results. Protected by a device-bound key in IndexedDB. Never sent to the server.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {status === "error" ? (
          <div className="flex flex-col gap-3">
            <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
              <TriangleAlert className="mt-0.5 size-4 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              className="inline-flex w-fit items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-accent"
              onClick={handleClear}
            >
              Clear stored keys and re-enter
            </button>
          </div>
        ) : status === "loading" ? (
          <p className="text-sm text-muted-foreground">Decrypting…</p>
        ) : hasStored && !editing ? (
          <>
            <div className="grid gap-3 sm:grid-cols-2">
              {CLIENT_KEY_NAMES.map((k) => (
                <div key={k} className="flex flex-col gap-1">
                  <label className="text-xs font-mono text-muted-foreground">{CLIENT_KEY_LABELS[k]}</label>
                  <div className="min-h-[80px] w-full rounded-md border bg-muted px-3 py-2 text-xs font-mono text-muted-foreground flex items-center select-none tracking-widest">
                    {"•".repeat(24)}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-3">
              {status === "saved" ? (
                <span className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-green-600 dark:text-green-400">
                  <Check className="size-4" /> Saved
                </span>
              ) : (
                <button
                  className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-accent"
                  onClick={() => setEditing(true)}
                >
                  Edit keys
                </button>
              )}
              <button
                className="inline-flex items-center gap-2 rounded-md border border-destructive/30 px-3 py-1.5 text-sm font-medium text-destructive hover:bg-destructive/10"
                onClick={handleClear}
              >
                Clear
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="grid gap-3 sm:grid-cols-2">
              {CLIENT_KEY_NAMES.map((k) => (
                <div key={k} className="flex flex-col gap-1">
                  <label className="text-xs font-mono text-muted-foreground">{CLIENT_KEY_LABELS[k]}</label>
                  <textarea
                    className="min-h-[80px] w-full resize-y rounded-md border bg-muted px-3 py-2 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-ring"
                    placeholder="-----BEGIN ... KEY-----"
                    value={keys[k]}
                    onChange={(e) => setKeys((prev) => ({ ...prev, [k]: e.target.value }))}
                  />
                </div>
              ))}
            </div>
            <div className="flex items-center gap-3">
              <button
                className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-accent"
                onClick={handleSave}
              >
                {status === "saved" ? <Check className="size-4" /> : null}
                {status === "saved" ? "Saved" : "Save keys"}
              </button>
              {editing && (
                <button
                  className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-accent"
                  onClick={() => setEditing(false)}
                >
                  Cancel
                </button>
              )}
              {!configured && (
                <span className="text-xs text-muted-foreground">Both keys required for client decryption.</span>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

function Settings() {
  return (
    <div className="flex flex-col gap-8">
      <div className="grid gap-4 md:grid-cols-2">
        <WalletCard />
        <NodeTypeCard />
        <LoggingCard />
        <EncryptionCard />
        <ClientEncryptionKeysCard />
      </div>
    </div>
  )
}
