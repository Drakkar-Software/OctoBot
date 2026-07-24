import { Check, Copy, Eye, EyeOff, TriangleAlert } from "lucide-react"
import { useEffect, useState } from "react"

import { ConfirmWalletSecretCopyDialog } from "@/components/Common/ConfirmWalletSecretCopyDialog"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useConfirmWalletSecretCopy } from "@/lib/use-confirm-wallet-secret-copy"
import { fetchOwnWalletExport } from "@/lib/wallet-export"

function SetupPrivateKeyPanelSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      <Skeleton className="h-12 w-full" />
      <div className="flex items-center justify-between">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-3 w-10" />
      </div>
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-8 w-32" />
    </div>
  )
}

export function SetupPrivateKeyPanel() {
  const [privateKey, setPrivateKey] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copiedKey, setCopiedKey] = useState(false)
  const [showKey, setShowKey] = useState(false)
  const walletSecretCopy = useConfirmWalletSecretCopy({
    onCopied: (secretType) => {
      if (secretType === "private_key") {
        setCopiedKey(true)
        setTimeout(() => setCopiedKey(false), 2000)
      }
    },
  })

  useEffect(() => {
    let cancelled = false
    const loadPrivateKey = async () => {
      setLoading(true)
      setError(null)
      try {
        const exportData = await fetchOwnWalletExport()
        if (!cancelled) {
          setPrivateKey(exportData.private_key)
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Failed to load private key",
          )
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }
    void loadPrivateKey()
    return () => {
      cancelled = true
    }
  }, [])

  const copyKey = () => {
    if (!privateKey) return
    walletSecretCopy.requestCopy(privateKey, "private_key")
  }

  if (loading) {
    return <SetupPrivateKeyPanelSkeleton />
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-start gap-2 rounded-md border border-warn/30 bg-warn/10 p-3 text-sm text-warn">
        <TriangleAlert className="mt-0.5 size-4 shrink-0" />
        <span>Never share your private key. Anyone with access to it controls your wallet.</span>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      {privateKey && (
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Private key
            </span>
            <button
              type="button"
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
              onClick={() => setShowKey((visible) => !visible)}
            >
              {showKey ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
              {showKey ? "Hide" : "Show"}
            </button>
          </div>
          <div className="flex items-center justify-between rounded-md border bg-muted px-3 py-2">
            <code className="text-xs break-all">
              {showKey
                ? privateKey
                : "•".repeat(Math.min(privateKey.length, 32))}
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
          <div className="flex justify-center pt-2">
            <Button type="button" variant="outline" onClick={copyKey}>
              Copy private key
            </Button>
          </div>
        </div>
      )}
      <ConfirmWalletSecretCopyDialog
        open={walletSecretCopy.confirmOpen}
        onOpenChange={walletSecretCopy.handleOpenChange}
        secretType={walletSecretCopy.pendingSecretType}
        onConfirm={walletSecretCopy.handleConfirm}
      />
    </div>
  )
}
