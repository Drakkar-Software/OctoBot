import { useMutation } from "@tanstack/react-query"
import { Plus, TriangleAlert } from "lucide-react"
import { useState } from "react"
import { WalletsService } from "@/client"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

export function AddWalletDialog({ onSuccess }: { onSuccess: () => void }) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [passphrase, setPassphrase] = useState("")
  const [privateKey, setPrivateKey] = useState("")
  const [seed, setSeed] = useState("")
  const [importMode, setImportMode] = useState(false)
  const [importBySeed, setImportBySeed] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isPrivateKeyValid = /^(0x)?[0-9a-fA-F]{64}$/.test(privateKey.trim())
  const isSeedValid = seed.trim().split(/\s+/).length >= 12

  const reset = () => {
    setName("")
    setPassphrase("")
    setPrivateKey("")
    setSeed("")
    setImportMode(false)
    setImportBySeed(false)
    setError(null)
  }

  const mutation = useMutation({
    mutationFn: () =>
      WalletsService.createWallet({
        requestBody: {
          passphrase,
          name: name.trim() || null,
          private_key: importMode && !importBySeed && privateKey.trim() ? privateKey.trim() : null,
          seed: importMode && importBySeed && seed.trim() ? seed.trim() : null,
        },
      }),
    onSuccess: () => {
      setOpen(false)
      reset()
      onSuccess()
    },
    onError: (e: unknown) => {
      const msg = e instanceof Error ? e.message : "Failed to add wallet"
      setError(msg)
    },
  })

  const isDisabled =
    passphrase.length < 8 ||
    (importMode && !importBySeed && !isPrivateKeyValid) ||
    (importMode && importBySeed && !isSeedValid) ||
    mutation.isPending

  const handleOpenChange = (v: boolean) => {
    if (!v) {
      reset()
      mutation.reset()
    }
    setOpen(v)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-accent"
        >
          <Plus className="size-4" />
          Add wallet
        </button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add wallet</DialogTitle>
          <DialogDescription>
            Create a new wallet or import one with a private key or seed phrase.
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
            <label
              htmlFor="wallet-name"
              className="text-xs font-medium text-muted-foreground"
            >
              Display name (optional)
            </label>
            <input
              id="wallet-name"
              className="rounded-md border border-rule bg-input px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-frost"
              placeholder="e.g. Alice"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1">
            <label
              htmlFor="wallet-passphrase"
              className="text-xs font-medium text-muted-foreground"
            >
              Passphrase
            </label>
            <input
              id="wallet-passphrase"
              type="password"
              className="rounded-md border border-rule bg-input px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-frost"
              placeholder="Choose a passphrase"
              value={passphrase}
              onChange={(e) => setPassphrase(e.target.value)}
            />
          </div>
          {importMode && (
            <>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground">
                  {importBySeed ? "Seed phrase" : "Private key"}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setImportBySeed((v) => !v)
                    setError(null)
                  }}
                  className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  <span className={`inline-flex w-7 h-4 rounded-full transition-colors ${importBySeed ? "bg-primary" : "bg-muted-foreground/40"} relative`}>
                    <span className={`absolute top-0.5 size-3 rounded-full bg-white transition-transform ${importBySeed ? "translate-x-3.5" : "translate-x-0.5"}`} />
                  </span>
                  {importBySeed ? "Use private key" : "Use seed phrase"}
                </button>
              </div>
              {importBySeed ? (
                <textarea
                  id="wallet-seed"
                  className="rounded-md border border-rule bg-input px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-frost font-mono resize-none"
                  placeholder="word1 word2 word3 … (12 or 24 words)"
                  rows={3}
                  value={seed}
                  onChange={(e) => setSeed(e.target.value)}
                />
              ) : (
                <input
                  id="wallet-private-key"
                  type="password"
                  className="rounded-md border border-rule bg-input px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-frost font-mono"
                  placeholder="0x..."
                  value={privateKey}
                  onChange={(e) => setPrivateKey(e.target.value)}
                />
              )}
            </>
          )}
          {error && (
            <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
              <TriangleAlert className="mt-0.5 size-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
          <button
            type="button"
            disabled={isDisabled}
            onClick={() => {
              if (passphrase.length < 8) {
                setError("Passphrase must be at least 8 characters")
                return
              }
              if (importMode && !importBySeed) {
                const pkClean = privateKey.trim().replace(/^0x/, "")
                if (!/^[0-9a-fA-F]{64}$/.test(pkClean)) {
                  setError(
                    "Private key must be a 64-character hex string (with or without 0x prefix)",
                  )
                  return
                }
              }
              if (importMode && importBySeed && !isSeedValid) {
                setError("Seed phrase must be at least 12 words")
                return
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
