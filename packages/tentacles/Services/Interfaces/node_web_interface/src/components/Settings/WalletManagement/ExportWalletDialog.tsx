import { Check, Copy, Download, Eye, EyeOff, TriangleAlert } from "lucide-react"
import { useState } from "react"
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
import { buildAuthHeader } from "@/lib/node-config"

export function ExportWalletDialog({ walletAddress, isOwnWallet }: { walletAddress: string; isOwnWallet: boolean }) {
  const [privateKey, setPrivateKey] = useState<string | null>(null)
  const [seed, setSeed] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copiedKey, setCopiedKey] = useState(false)
  const [copiedSeed, setCopiedSeed] = useState(false)
  const [showKey, setShowKey] = useState(false)
  const [showSeed, setShowSeed] = useState(false)
  const [passphraseInput, setPassphraseInput] = useState("")

  const fetchWalletExport = async (passphrase?: string) => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (!isOwnWallet) {
        params.set("address", walletAddress)
        params.set("passphrase", passphrase ?? "")
      }
      const url = `/api/v1/setup/wallet/export${params.size ? `?${params}` : ""}`
      const res = await fetch(url, {
        headers: { Authorization: await buildAuthHeader() },
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setPrivateKey(data.private_key)
      setSeed(data.seed ?? null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to export wallet")
    } finally {
      setLoading(false)
    }
  }

  const copyKey = () => {
    if (!privateKey) return
    navigator.clipboard.writeText(privateKey)
    setCopiedKey(true)
    setTimeout(() => setCopiedKey(false), 2000)
  }

  const copySeed = () => {
    if (!seed) return
    navigator.clipboard.writeText(seed)
    setCopiedSeed(true)
    setTimeout(() => setCopiedSeed(false), 2000)
  }

  const onOpenChange = (open: boolean) => {
    if (open && isOwnWallet) {
      void fetchWalletExport()
    }
    if (!open) {
      setPrivateKey(null)
      setSeed(null)
      setError(null)
      setShowKey(false)
      setShowSeed(false)
      setPassphraseInput("")
    }
  }

  return (
    <Dialog onOpenChange={onOpenChange}>
      <Tooltip>
        <TooltipTrigger asChild>
          <DialogTrigger asChild>
            <button
              type="button"
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
              Never share your private key or seed phrase. Store them in a secure location.
            </span>
          </div>
          {!isOwnWallet && !privateKey && (
            <div className="flex flex-col gap-2">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Wallet passphrase
              </label>
              <div className="flex gap-2">
                <input
                  type="password"
                  className="flex-1 rounded-md border bg-background px-3 py-2 text-sm"
                  placeholder="Enter wallet passphrase"
                  value={passphraseInput}
                  onChange={(e) => setPassphraseInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && passphraseInput) void fetchWalletExport(passphraseInput)
                  }}
                />
                <button
                  type="button"
                  className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                  disabled={!passphraseInput || loading}
                  onClick={() => void fetchWalletExport(passphraseInput)}
                >
                  {loading ? "…" : "Decrypt"}
                </button>
              </div>
            </div>
          )}
          {loading && !privateKey && isOwnWallet && (
            <p className="text-sm text-muted-foreground">Decrypting wallet…</p>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
          {privateKey && (
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Private key</span>
                <button
                  type="button"
                  className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
                  onClick={() => setShowKey((v) => !v)}
                >
                  {showKey ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
                  {showKey ? "Hide" : "Show"}
                </button>
              </div>
              <div className="flex items-center justify-between rounded-md border bg-muted px-3 py-2">
                <code className="text-xs break-all">
                  {showKey ? privateKey : "•".repeat(Math.min(privateKey.length, 32))}
                </code>
                <button
                  type="button"
                  className="ml-3 shrink-0 text-muted-foreground hover:text-foreground"
                  onClick={copyKey}
                  title="Copy private key"
                >
                  {copiedKey ? <Check className="size-4" /> : <Copy className="size-4" />}
                </button>
              </div>
            </div>
          )}
          {seed && (
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Seed phrase</span>
                <button
                  type="button"
                  className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
                  onClick={() => setShowSeed((v) => !v)}
                >
                  {showSeed ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
                  {showSeed ? "Hide" : "Show"}
                </button>
              </div>
              <div className="flex items-center justify-between rounded-md border bg-muted px-3 py-2">
                <code className="text-xs break-all">
                  {showSeed ? seed : "•".repeat(Math.min(seed.length, 32))}
                </code>
                <button
                  type="button"
                  className="ml-3 shrink-0 text-muted-foreground hover:text-foreground"
                  onClick={copySeed}
                  title="Copy seed phrase"
                >
                  {copiedSeed ? <Check className="size-4" /> : <Copy className="size-4" />}
                </button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
