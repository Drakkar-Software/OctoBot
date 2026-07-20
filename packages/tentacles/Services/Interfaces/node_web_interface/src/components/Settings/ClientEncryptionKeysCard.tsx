import { Check, KeyRound, ShieldCheck, TriangleAlert, X } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
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
  saveClientKeys,
} from "@/lib/device-key"
import { fetchNodeConfig } from "@/lib/node-config"

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

export function ClientEncryptionKeysCard() {
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
    void (async () => {
      try {
        const data = await fetchNodeConfig()
        setServerEnabled(data.tasks_encryption_enabled ?? false)
        setServerEnvVars(data.server_encryption_env_vars ?? [])
      } catch {
        setServerEnabled(false)
      }
    })()
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
    <Card className="relative">
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
                type="button"
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
              <div className="flex flex-col gap-3">
                {CLIENT_KEY_NAMES.map((k) => (
                  <div key={k} className="flex flex-col gap-1">
                    <span className="text-xs font-mono text-muted-foreground">
                      {CLIENT_KEY_LABELS[k]}
                    </span>
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
                    type="button"
                    className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-accent"
                    onClick={() => setEditing(true)}
                  >
                    Edit keys
                  </button>
                )}
                <button
                  type="button"
                  className="inline-flex items-center gap-2 rounded-md border border-destructive/30 px-3 py-1.5 text-sm font-medium text-destructive hover:bg-destructive/10"
                  onClick={handleClear}
                >
                  Clear
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="flex flex-col gap-3">
                {CLIENT_KEY_NAMES.map((k) => (
                  <div key={k} className="flex flex-col gap-1">
                    <label
                      htmlFor={`client-key-${k}`}
                      className="text-xs font-mono text-muted-foreground"
                    >
                      {CLIENT_KEY_LABELS[k]}
                    </label>
                    <textarea
                      id={`client-key-${k}`}
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
                  type="button"
                  className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-accent"
                  onClick={handleSave}
                >
                  {status === "saved" ? <Check className="size-4" /> : null}
                  {status === "saved" ? "Saved" : "Save keys"}
                </button>
                {editing && (
                  <button
                    type="button"
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
