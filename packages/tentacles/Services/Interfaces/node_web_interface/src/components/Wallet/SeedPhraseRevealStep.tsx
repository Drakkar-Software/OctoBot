import { Copy, TriangleAlert } from "lucide-react"
import { useState } from "react"

import { ConfirmWalletSecretCopyDialog } from "@/components/Common/ConfirmWalletSecretCopyDialog"
import { SetupStepHeader } from "@/components/Setup/SetupStepHeader"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  SeedPhraseWordGrid,
  SeedPhraseWordGridCell,
} from "@/components/Wallet/SeedPhraseWordGrid"
import { splitSeedPhraseWords } from "@/lib/seed-onboarding"
import { useConfirmWalletSecretCopy } from "@/lib/use-confirm-wallet-secret-copy"

export type SeedPhraseRevealStepProps = {
  seed: string
  step?: number
  total?: number
  onContinue: () => void
}

export function SeedPhraseRevealStep({
  seed,
  step,
  total,
  onContinue,
}: SeedPhraseRevealStepProps) {
  const words = splitSeedPhraseWords(seed)
  const [savedOffline, setSavedOffline] = useState(false)

  const walletSecretCopy = useConfirmWalletSecretCopy()

  const canContinue = savedOffline

  const copyPhrase = () => {
    walletSecretCopy.requestCopy(seed, "seed_phrase")
  }

  return (
    <>
      <div className="flex flex-col gap-6">
        <SetupStepHeader
          step={step}
          total={total}
          title="Save your seed phrase"
          subtitle="Write down all words in order. You need them to recover this wallet."
        />
        <div className="flex items-start gap-2 rounded-md border border-warn/30 bg-warn/10 p-3 text-sm text-warn">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" />
          <span>
            Anyone with these words can control your wallet. Never share them online.
          </span>
        </div>
        <SeedPhraseWordGrid>
          {words.map((word, index) => (
            <SeedPhraseWordGridCell key={`${index}-${word}`} index={index}>
              {word}
            </SeedPhraseWordGridCell>
          ))}
        </SeedPhraseWordGrid>
        <Button type="button" variant="outline" onClick={copyPhrase}>
          <Copy className="size-4" />
          Copy seed phrase
        </Button>
        <div className="flex items-start gap-3">
          <Checkbox
            id="seed-saved-offline"
            checked={savedOffline}
            onCheckedChange={(checked) => setSavedOffline(checked === true)}
          />
          <Label
            htmlFor="seed-saved-offline"
            className="text-sm font-normal leading-snug"
          >
            I saved it offline
          </Label>
        </div>
        <LoadingButton
          type="button"
          disabled={!canContinue}
          onClick={onContinue}
        >
          Continue
        </LoadingButton>
      </div>
      <ConfirmWalletSecretCopyDialog
        open={walletSecretCopy.confirmOpen}
        onOpenChange={walletSecretCopy.handleOpenChange}
        secretType={walletSecretCopy.pendingSecretType}
        onConfirm={walletSecretCopy.handleConfirm}
      />
    </>
  )
}
