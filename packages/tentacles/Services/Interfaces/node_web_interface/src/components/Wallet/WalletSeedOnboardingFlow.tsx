import { useState } from "react"

import { SeedPhraseQuizStep } from "@/components/Wallet/SeedPhraseQuizStep"
import { SeedPhraseRevealStep } from "@/components/Wallet/SeedPhraseRevealStep"

type FlowStep = "reveal" | "quiz"

export type WalletSeedOnboardingFlowProps = {
  seed: string
  revealStep?: number
  quizStep?: number
  totalSteps?: number
  onComplete: () => void
}

export function WalletSeedOnboardingFlow({
  seed,
  revealStep,
  quizStep,
  totalSteps,
  onComplete,
}: WalletSeedOnboardingFlowProps) {
  const [step, setStep] = useState<FlowStep>("reveal")

  if (step === "reveal") {
    return (
      <SeedPhraseRevealStep
        seed={seed}
        step={revealStep}
        total={totalSteps}
        onContinue={() => setStep("quiz")}
      />
    )
  }

  return (
    <SeedPhraseQuizStep
      seed={seed}
      step={quizStep}
      total={totalSteps}
      onPrevious={() => setStep("reveal")}
      onComplete={onComplete}
    />
  )
}
