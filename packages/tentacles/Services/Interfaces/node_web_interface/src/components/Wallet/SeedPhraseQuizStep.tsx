import { useMemo, useState } from "react"

import { SetupStepHeader } from "@/components/Setup/SetupStepHeader"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  areSeedQuizAnswersCorrect,
  pickSeedQuizPositions,
  splitSeedPhraseWords,
} from "@/lib/seed-onboarding"

export type SeedPhraseQuizStepProps = {
  seed: string
  step?: number
  total?: number
  onComplete: () => void
  onPrevious: () => void
}

export function SeedPhraseQuizStep({
  seed,
  step,
  total,
  onComplete,
  onPrevious,
}: SeedPhraseQuizStepProps) {
  const words = useMemo(() => splitSeedPhraseWords(seed), [seed])
  const positions = useMemo(
    () => pickSeedQuizPositions(words.length, 3),
    [words.length],
  )
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [error, setError] = useState<string | null>(null)

  const allFilled = positions.every((index) => answers[index]?.trim())

  const handleSubmit = () => {
    if (!allFilled) {
      setError("Fill in every word.")
      return
    }
    if (!areSeedQuizAnswersCorrect(words, positions, answers)) {
      setError("One or more words do not match. Check your phrase and try again.")
      return
    }
    setError(null)
    onComplete()
  }

  return (
    <div className="flex flex-col gap-6">
      <SetupStepHeader
        step={step}
        total={total}
        title="Confirm your seed phrase"
        subtitle="Enter the missing words from your saved phrase."
      />
      <div className="flex flex-col gap-4">
        {positions.map((index) => (
          <div key={index} className="flex flex-col gap-1">
            <label
              htmlFor={`seed-quiz-${index}`}
              className="text-sm font-medium"
            >
              Word #{index + 1}
            </label>
            <Input
              id={`seed-quiz-${index}`}
              className="font-mono"
              autoComplete="off"
              value={answers[index] ?? ""}
              onChange={(event) => {
                setAnswers((prev) => ({
                  ...prev,
                  [index]: event.target.value,
                }))
                setError(null)
              }}
            />
          </div>
        ))}
      </div>
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
      <div className="flex flex-col gap-2 sm:flex-row sm:justify-between">
        <Button type="button" variant="outline" onClick={onPrevious}>
          Previous
        </Button>
        <LoadingButton
          type="button"
          disabled={!allFilled}
          onClick={handleSubmit}
        >
          Continue
        </LoadingButton>
      </div>
    </div>
  )
}
