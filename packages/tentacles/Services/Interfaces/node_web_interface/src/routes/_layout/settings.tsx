import { createFileRoute } from "@tanstack/react-router"
import { CheckCircle2, Copy, Download, FileText, Network, QrCode, Server, ShieldCheck, ShieldOff, Sliders, TriangleAlert, Wallet } from "lucide-react"
import { useEffect, useState } from "react"
import QRCode from "react-qr-code"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/settings")({
  component: Settings,
  head: () => ({
    meta: [{ title: "Settings" }],
  }),
})

function LoggingCard() {
  const [enabled, setEnabled] = useState<boolean | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetch("/api/v1/nodes/config", { credentials: "include" })
      .then((r) => r.json())
      .then((data) => setEnabled(data.use_dedicated_log_file_per_automation ?? true))
      .catch(() => setEnabled(true))
  }, [])

  const handleToggle = async (value: boolean) => {
    setLoading(true)
    try {
      const res = await fetch("/api/v1/nodes/config", {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ use_dedicated_log_file_per_automation: value }),
      })
      const data = await res.json()
      setEnabled(data.use_dedicated_log_file_per_automation)
    } catch {
      // keep previous value on error
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="size-4" />
          Logging
        </CardTitle>
        <CardDescription>
          Per-bot log files and diagnostic settings.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex flex-col gap-1">
            <Label htmlFor="per-bot-logs">Per-bot log files</Label>
            <span className="text-xs text-muted-foreground">
              Write a dedicated log file for each bot run in <code>logs/automations/</code>.
              Changes apply immediately but reset on restart.
            </span>
          </div>
          <Checkbox
            id="per-bot-logs"
            checked={enabled ?? true}
            disabled={enabled === null || loading}
            onCheckedChange={(v) => handleToggle(Boolean(v))}
          />
        </div>
      </CardContent>
    </Card>
  )
}

function buildAuthHeader() {
  const username = localStorage.getItem("auth_username") || "node"
  const password = localStorage.getItem("auth_password") || ""
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
        headers: { Authorization: buildAuthHeader() },
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

  const onOpenChange = (open: boolean) => {
    if (open) {
      const address = localStorage.getItem("auth_username") || ""
      const passphrase = localStorage.getItem("auth_password") || ""
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
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetch("/api/v1/nodes/config", { credentials: "include" })
      .then((r) => r.json())
      .then((data) => setNodeType(data.node_type ?? "standalone"))
      .catch(() => setNodeType("standalone"))
  }, [])

  const select = async (value: NodeType) => {
    if (loading || value === nodeType) return
    setLoading(true)
    try {
      const res = await fetch("/api/v1/nodes/config", {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ node_type: value }),
      })
      const data = await res.json()
      setNodeType(data.node_type)
    } catch {
      // keep previous value on error
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sliders className="size-4" />
          Node type
        </CardTitle>
        <CardDescription>
          Choose how this node runs.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-3">
        <button
          disabled={loading || nodeType === null}
          onClick={() => select("standalone")}
          className={`flex flex-col items-center gap-2 rounded-lg border p-4 text-sm transition-colors ${
            nodeType === "standalone"
              ? "border-primary bg-primary/5 text-primary"
              : "hover:border-primary/40 hover:bg-muted text-muted-foreground"
          }`}
        >
          <Server className="size-6" />
          Standalone
        </button>
        <div className="relative flex flex-col items-center gap-2 rounded-lg border p-4 text-sm opacity-50 cursor-not-allowed text-muted-foreground">
          <Network className="size-6" />
          Master / Replica
          <span className="absolute -top-2 right-2 rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground border">
            Coming soon
          </span>
        </div>
      </CardContent>
    </Card>
  )
}

function EncryptionCard() {
  const [enabled, setEnabled] = useState<boolean | null>(null)

  useEffect(() => {
    fetch("/api/v1/nodes/config", { credentials: "include" })
      .then((r) => r.json())
      .then((data) => setEnabled(data.tasks_encryption_enabled ?? false))
      .catch(() => setEnabled(false))
  }, [])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldCheck className="size-4" />
          Task encryption
        </CardTitle>
        <CardDescription>
          End-to-end encryption status for task inputs and outputs.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {enabled === null ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : enabled ? (
          <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
            <CheckCircle2 className="size-4 shrink-0" />
            Enabled — all task encryption keys are configured.
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <ShieldOff className="size-4 shrink-0" />
              Disabled — define the following environment variables to enable:
            </div>
            <ul className="text-xs font-mono text-muted-foreground flex flex-col gap-0.5 ml-6 list-disc">
              <li>TASKS_INPUTS_RSA_PRIVATE_KEY</li>
              <li>TASKS_INPUTS_ECDSA_PUBLIC_KEY</li>
              <li>TASKS_OUTPUTS_RSA_PUBLIC_KEY</li>
              <li>TASKS_OUTPUTS_ECDSA_PRIVATE_KEY</li>
              <li>TASKS_INPUTS_RSA_PUBLIC_KEY</li>
              <li>TASKS_INPUTS_ECDSA_PRIVATE_KEY</li>
              <li>TASKS_OUTPUTS_RSA_PRIVATE_KEY</li>
              <li>TASKS_OUTPUTS_ECDSA_PUBLIC_KEY</li>
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function Settings() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Tune security, node behavior, and integrations.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <WalletCard />
        <NodeTypeCard />
        <LoggingCard />
        <EncryptionCard />
      </div>
    </div>
  )
}
