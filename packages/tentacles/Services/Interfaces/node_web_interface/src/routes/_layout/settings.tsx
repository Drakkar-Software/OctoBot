import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import {
  Check,
  Copy,
  Download,
  FileText,
  KeyRound,
  LogOut,
  Network,
  Plus,
  QrCode,
  Server,
  ShieldCheck,
  Sliders,
  Trash2,
  TriangleAlert,
  Wallet,
  X,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { QRCode } from "react-qr-code"
import { type WalletInfo, WalletsService } from "@/client"
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
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import useAuth from "@/hooks/useAuth"
import type { ClientKeys } from "@/lib/client-encryption"
import {
  areClientKeysConfigured,
  CLIENT_KEY_LABELS,
  CLIENT_KEY_NAMES,
  emptyKeys,
} from "@/lib/client-encryption"
import {
  clearClientKeys,
  hasStoredClientKeys,
  loadClientKeys,
  loadPassword,
  saveClientKeys,
} from "@/lib/device-key"
import { truncateAddress } from "@/lib/wallet-utils"

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
      .then((data) =>
        setEnabled(data.use_dedicated_log_file_per_automation ?? true),
      )
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
    if (open) {
      void fetchPrivateKey()
    }
    if (!open) {
      setPrivateKey(null)
      setError(null)
    }
  }

  return (
    <Dialog onOpenChange={onOpenChange}>
      <Tooltip>
        <TooltipTrigger asChild>
          <DialogTrigger asChild>
            <button
              className="text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Export wallet"
            >
              <Download className="size-4" />
            </button>
          </DialogTrigger>
        </TooltipTrigger>
        <TooltipContent side="left">Export wallet</TooltipContent>
      </Tooltip>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Export wallet</DialogTitle>
          <DialogDescription>
            Keep your private key safe. Anyone with access to it controls your
            wallet.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex items-start gap-2 rounded-md border border-warn/30 bg-warn/10 p-3 text-sm text-warn">
            <TriangleAlert className="mt-0.5 size-4 shrink-0" />
            <span>
              Never share your private key. Store it in a secure location.
            </span>
          </div>
          {loading && (
            <p className="text-sm text-muted-foreground">Decrypting wallet…</p>
          )}
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
              {copied && (
                <p className="text-xs text-muted-foreground">Copied!</p>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function PairDeviceDialog() {
  const [qrValue, setQrValue] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const buildQrValue = async () => {
    setError(null)
    try {
      const address = localStorage.getItem("auth_username") || ""
      const passphrase = (await loadPassword()) ?? ""
      if (!address || !passphrase) {
        throw new Error(
          "No active wallet session — log out and back in to refresh device key.",
        )
      }
      setQrValue(
        JSON.stringify({
          url: window.location.origin,
          address,
          passphrase,
        }),
      )
    } catch (e) {
      console.error("PairDeviceDialog: failed to build QR value", e)
      setError(e instanceof Error ? e.message : "Failed to build QR code")
    }
  }

  const onOpenChange = (open: boolean) => {
    if (open) {
      void buildQrValue()
    }
    if (!open) {
      setQrValue(null)
      setError(null)
    }
  }

  return (
    <Dialog onOpenChange={onOpenChange}>
      <Tooltip>
        <TooltipTrigger asChild>
          <DialogTrigger asChild>
            <button
              className="text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Pair device"
            >
              <QrCode className="size-4" />
            </button>
          </DialogTrigger>
        </TooltipTrigger>
        <TooltipContent side="left">Pair device</TooltipContent>
      </Tooltip>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Pair mobile device</DialogTitle>
          <DialogDescription>
            Scan this QR code with your OctoBot mobile app to connect to this
            node.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col items-center gap-4">
          <div className="flex items-start gap-2 rounded-md border border-warn/30 bg-warn/10 p-3 text-sm text-warn w-full">
            <TriangleAlert className="mt-0.5 size-4 shrink-0" />
            <span>
              Only scan on a trusted device. The QR code contains your
              passphrase.
            </span>
          </div>
          {error && (
            <p className="text-sm text-destructive text-center">{error}</p>
          )}
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
        <CardDescription>How this node is configured to run.</CardDescription>
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
          The node type can only be changed from the CLI. Use the{" "}
          <code>--node-type</code> flag when starting the node.
        </span>
      </CardContent>
    </Card>
  )
}

function ClientEncryptionKeysCard() {
  const [keys, setKeys] = useState<ClientKeys>(emptyKeys)
  const [status, setStatus] = useState<"loading" | "ready" | "saved" | "error">(
    "loading",
  )
  const [hasStored, setHasStored] = useState(false)
  const [editing, setEditing] = useState(false)
  const [error, setError] = useState("")
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const configured = areClientKeysConfigured(keys)
  const [serverEnabled, setServerEnabled] = useState<boolean | null>(null)
  const [serverEnvVars, setServerEnvVars] = useState<string[]>([])

  useEffect(() => {
    fetch("/api/v1/nodes/config", { credentials: "include" })
      .then((r) => r.json())
      .then((data) => {
        setServerEnabled(data.tasks_encryption_enabled ?? false)
        setServerEnvVars(data.server_encryption_env_vars ?? [])
      })
      .catch(() => setServerEnabled(false))
  }, [])

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
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
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
        <StatusIndicator
          enabled={
            serverEnabled === null
              ? null
              : serverEnabled === true && configured && hasStored
          }
        />
      </div>
      <CardHeader className="pr-12">
        <CardTitle className="flex items-center gap-2">
          <KeyRound className="size-4" />
          Encryption keys
        </CardTitle>
        <CardDescription>
          Server-side and browser-stored client keys for end-to-end task
          encryption.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Server keys
          </span>
          {serverEnabled === null ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : serverEnabled ? (
            <span className="inline-flex items-center gap-1.5 text-xs text-pos">
              <ShieldCheck className="size-3.5" /> All server encryption keys
              are configured.
            </span>
          ) : (
            <div className="flex flex-col gap-1.5">
              <span className="text-xs text-muted-foreground">
                Set these environment variables to enable:
              </span>
              <ul className="text-xs font-mono text-muted-foreground flex flex-col gap-0.5 ml-6 list-disc">
                {serverEnvVars.map((v) => (
                  <li key={v}>{v}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
        <div className="border-t" />
        <div className="flex flex-col gap-4">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Client keys
          </span>
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
                    <label className="text-xs font-mono text-muted-foreground">
                      {CLIENT_KEY_LABELS[k]}
                    </label>
                    <div className="min-h-[80px] w-full rounded-md border bg-muted px-3 py-2 text-xs font-mono text-muted-foreground flex items-center select-none tracking-widest">
                      {"•".repeat(24)}
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-3">
                {status === "saved" ? (
                  <span className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-pos">
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
                    <label className="text-xs font-mono text-muted-foreground">
                      {CLIENT_KEY_LABELS[k]}
                    </label>
                    <textarea
                      className="min-h-[80px] w-full resize-y rounded-md border bg-muted px-3 py-2 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-ring"
                      placeholder="-----BEGIN ... KEY-----"
                      value={keys[k]}
                      onChange={(e) =>
                        setKeys((prev) => ({ ...prev, [k]: e.target.value }))
                      }
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
                  <span className="text-xs text-muted-foreground">
                    Both keys required for client decryption.
                  </span>
                )}
              </div>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function AddWalletDialog({ onSuccess }: { onSuccess: () => void }) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [passphrase, setPassphrase] = useState("")
  const [privateKey, setPrivateKey] = useState("")
  const [importMode, setImportMode] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () =>
      WalletsService.createWallet({
        requestBody: {
          passphrase,
          name: name.trim() || null,
          private_key:
            importMode && privateKey.trim() ? privateKey.trim() : null,
        },
      }),
    onSuccess: () => {
      setOpen(false)
      setName("")
      setPassphrase("")
      setPrivateKey("")
      setImportMode(false)
      setError(null)
      onSuccess()
    },
    onError: (e: unknown) => {
      const msg = e instanceof Error ? e.message : "Failed to add wallet"
      setError(msg)
    },
  })

  const handleOpenChange = (v: boolean) => {
    if (!v) {
      setName("")
      setPassphrase("")
      setPrivateKey("")
      setImportMode(false)
      setError(null)
      mutation.reset()
    }
    setOpen(v)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <button className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-accent">
          <Plus className="size-4" />
          Add wallet
        </button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add wallet</DialogTitle>
          <DialogDescription>
            Create a new wallet or import one with a private key.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                setImportMode(false)
                setError(null)
              }}
              className={`flex-1 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors ${!importMode ? "bg-primary text-primary-foreground" : "hover:bg-accent"}`}
            >
              Create new
            </button>
            <button
              type="button"
              onClick={() => {
                setImportMode(true)
                setError(null)
              }}
              className={`flex-1 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors ${importMode ? "bg-primary text-primary-foreground" : "hover:bg-accent"}`}
            >
              Import
            </button>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-muted-foreground">
              Display name (optional)
            </label>
            <input
              className="rounded-md border border-rule bg-input px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-frost"
              placeholder="e.g. Alice"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-muted-foreground">
              Passphrase
            </label>
            <input
              type="password"
              className="rounded-md border border-rule bg-input px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-frost"
              placeholder="Choose a passphrase"
              value={passphrase}
              onChange={(e) => setPassphrase(e.target.value)}
            />
          </div>
          {importMode && (
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-muted-foreground">
                Private key
              </label>
              <input
                type="password"
                className="rounded-md border border-rule bg-input px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-frost font-mono"
                placeholder="0x..."
                value={privateKey}
                onChange={(e) => setPrivateKey(e.target.value)}
              />
            </div>
          )}
          {error && (
            <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
              <TriangleAlert className="mt-0.5 size-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
          <button
            type="button"
            disabled={
              passphrase.length < 8 ||
              (importMode &&
                !/^(0x)?[0-9a-fA-F]{64}$/.test(privateKey.trim())) ||
              mutation.isPending
            }
            onClick={() => {
              if (passphrase.length < 8) {
                setError("Passphrase must be at least 8 characters")
                return
              }
              if (importMode) {
                const pkClean = privateKey.trim().replace(/^0x/, "")
                if (!/^[0-9a-fA-F]{64}$/.test(pkClean)) {
                  setError(
                    "Private key must be a 64-character hex string (with or without 0x prefix)",
                  )
                  return
                }
              }
              mutation.mutate()
            }}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {mutation.isPending
              ? "Adding…"
              : importMode
                ? "Import wallet"
                : "Create wallet"}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function RemoveWalletDialog({
  wallet,
  onSuccess,
}: {
  wallet: WalletInfo
  onSuccess: () => void
}) {
  const [open, setOpen] = useState(false)

  const mutation = useMutation({
    mutationFn: () => WalletsService.deleteWallet({ address: wallet.address }),
    onSuccess: () => {
      setOpen(false)
      onSuccess()
    },
  })

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        mutation.reset()
        setOpen(v)
      }}
    >
      <DialogTrigger asChild>
        <button
          className="text-muted-foreground hover:text-destructive transition-colors"
          title="Remove wallet"
          aria-label="Remove wallet"
        >
          <Trash2 className="size-4" />
        </button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Remove wallet</DialogTitle>
          <DialogDescription>
            This will permanently remove{" "}
            <span className="font-mono">
              {wallet.name || truncateAddress(wallet.address)}
            </span>{" "}
            from this node.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex items-start gap-2 rounded-md border border-warn/30 bg-warn/10 p-3 text-sm text-warn">
            <TriangleAlert className="mt-0.5 size-4 shrink-0" />
            <span>
              Tasks associated with this wallet will become orphaned (visible to
              admins only). This action cannot be undone.
            </span>
          </div>
          {mutation.isError && (
            <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
              <TriangleAlert className="mt-0.5 size-4 shrink-0" />
              <span>
                {mutation.error instanceof Error
                  ? mutation.error.message
                  : "Failed to remove wallet"}
              </span>
            </div>
          )}
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-accent"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={mutation.isPending}
              onClick={() => mutation.mutate()}
              className="inline-flex items-center gap-2 rounded-md bg-destructive px-3 py-1.5 text-sm font-medium text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50"
            >
              {mutation.isPending ? "Removing…" : "Remove"}
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function WalletRow({
  wallet,
  onRefresh,
  showRemove = true,
  currentUserAddress = "",
}: {
  wallet: WalletInfo
  onRefresh: () => void
  showRemove?: boolean
  currentUserAddress?: string
}) {
  const [editing, setEditing] = useState(false)
  const [nameValue, setNameValue] = useState(wallet.name ?? "")
  const [renameError, setRenameError] = useState<string | null>(null)

  useEffect(() => {
    if (!editing) setNameValue(wallet.name ?? "")
  }, [wallet.name, editing])

  const mutation = useMutation({
    mutationFn: (name: string | null) =>
      WalletsService.updateWallet({
        address: wallet.address,
        requestBody: { name },
      }),
    onSuccess: () => {
      setEditing(false)
      setRenameError(null)
      onRefresh()
    },
    onError: (e: unknown) => {
      setRenameError(e instanceof Error ? e.message : "Failed to rename wallet")
    },
  })

  const handleSave = () => {
    mutation.mutate(nameValue.trim() || null)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSave()
    if (e.key === "Escape") {
      setEditing(false)
      setNameValue(wallet.name ?? "")
    }
  }

  return (
    <div className="flex items-center gap-3 rounded-lg border p-3">
      <div className="flex-1 min-w-0 flex flex-col gap-0.5">
        {editing ? (
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <input
                className="rounded border border-rule bg-input px-2 py-0.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-frost"
                value={nameValue}
                onChange={(e) => setNameValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Display name"
              />
              <button
                onClick={handleSave}
                disabled={mutation.isPending}
                className="text-xs text-primary hover:underline disabled:opacity-50"
              >
                {mutation.isPending ? "Saving…" : "Save"}
              </button>
              <button
                onClick={() => {
                  setEditing(false)
                  setNameValue(wallet.name ?? "")
                  setRenameError(null)
                  mutation.reset()
                }}
                className="text-xs text-muted-foreground hover:underline"
              >
                Cancel
              </button>
            </div>
            {renameError && (
              <span className="text-xs text-destructive">{renameError}</span>
            )}
          </div>
        ) : (
          <button
            onClick={() => setEditing(true)}
            className="flex items-center gap-1.5 w-fit text-left group"
            title="Click to edit name"
          >
            <span className="text-sm font-medium group-hover:underline underline-offset-2">
              {wallet.name || (
                <span className="text-muted-foreground italic">No name</span>
              )}
            </span>
          </button>
        )}
        <span className="text-xs text-muted-foreground font-mono">
          {truncateAddress(wallet.address)}
        </span>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {wallet.address.toLowerCase() === currentUserAddress.toLowerCase() && (
          <>
            <ExportWalletDialog />
            <PairDeviceDialog />
          </>
        )}
        {wallet.is_admin && (
          <Tooltip>
            <TooltipTrigger asChild>
              <span>
                <ShieldCheck className="size-4 text-primary" />
              </span>
            </TooltipTrigger>
            <TooltipContent side="left">Admin wallet</TooltipContent>
          </Tooltip>
        )}
        {wallet.is_admin === false && showRemove && (
          <RemoveWalletDialog wallet={wallet} onSuccess={onRefresh} />
        )}
      </div>
    </div>
  )
}

function WalletManagementCard() {
  const queryClient = useQueryClient()
  const { user, logout } = useAuth()
  const { data: wallets = [], isLoading } = useQuery({
    queryKey: ["wallets"],
    queryFn: () => WalletsService.listWallets(),
  })

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["wallets"] })
  }

  const currentAddress = localStorage.getItem("auth_username") ?? ""
  const displayedWallets = user?.is_superuser
    ? wallets
    : wallets.filter((w) => w.address === currentAddress)

  return (
    <Card className="relative md:col-span-2">
      <div className="absolute right-4 top-4">
        <Button variant="outline" size="sm" onClick={() => void logout()}>
          <LogOut className="size-4" />
          Logout
        </Button>
      </div>
      <CardHeader className="pr-28">
        <CardTitle className="flex items-center gap-2">
          <Wallet className="size-4" />
          Wallet management
        </CardTitle>
        <CardDescription>
          Manage wallets that can log in to this node. Each wallet has its own
          passphrase and task visibility.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading wallets…</p>
        ) : (
          <>
            <div className="flex flex-col gap-2">
              {displayedWallets.map((wallet) => (
                <WalletRow
                  key={wallet.address}
                  wallet={wallet}
                  onRefresh={refresh}
                  showRemove={user?.is_superuser === true}
                  currentUserAddress={currentAddress}
                />
              ))}
            </div>
            {user?.is_superuser && <AddWalletDialog onSuccess={refresh} />}
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
        <NodeTypeCard />
        <LoggingCard />
        <ClientEncryptionKeysCard />
        <WalletManagementCard />
      </div>
    </div>
  )
}
