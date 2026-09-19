import { useQuery, useQueryClient } from "@tanstack/react-query"
import { ShieldAlert } from "lucide-react"
import { useState } from "react"

import { SaveRecoveryPhraseDialog } from "@/components/Account/SaveRecoveryPhraseDialog"
import { Button } from "@/components/ui/button"
import {
  fetchRecoveryPhrase,
  fetchRecoveryPhraseStatus,
} from "@/lib/recovery-phrase"

export function SaveAccountBanner() {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [seed, setSeed] = useState<string | null>(null)
  const [loadingPhrase, setLoadingPhrase] = useState(false)

  const { data: status } = useQuery({
    queryKey: ["recovery-phrase-status"],
    queryFn: fetchRecoveryPhraseStatus,
  })

  const showBanner =
    status?.has_recovery_phrase === true && status.recovery_phrase_saved === false

  const openSaveFlow = async () => {
    setLoadingPhrase(true)
    try {
      const phrase = await fetchRecoveryPhrase()
      setSeed(phrase)
      setDialogOpen(true)
    } finally {
      setLoadingPhrase(false)
    }
  }

  const handleSaved = () => {
    void queryClient.invalidateQueries({ queryKey: ["recovery-phrase-status"] })
    setSeed(null)
  }

  if (!showBanner) {
    return null
  }

  return (
    <>
      <div
        className="flex flex-col gap-3 rounded-lg border border-primary/20 bg-primary/5 p-4 sm:flex-row sm:items-center sm:justify-between"
        data-testid="save-account-banner"
      >
        <div className="flex items-start gap-3">
          <ShieldAlert className="mt-0.5 size-5 shrink-0 text-primary" />
          <div className="flex flex-col gap-1">
            <p className="font-medium">Save your account</p>
            <p className="text-sm text-muted-foreground">
              Back up your recovery phrase so you can get back in if you forget
              your passphrase.
            </p>
          </div>
        </div>
        <Button
          type="button"
          onClick={() => void openSaveFlow()}
          disabled={loadingPhrase}
          className="shrink-0"
        >
          {loadingPhrase ? "Loading…" : "Save recovery phrase"}
        </Button>
      </div>
      {seed ? (
        <SaveRecoveryPhraseDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          seed={seed}
          onSaved={handleSaved}
        />
      ) : null}
    </>
  )
}
