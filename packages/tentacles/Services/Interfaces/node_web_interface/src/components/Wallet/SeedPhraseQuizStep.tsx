import { useMemo, useState } from "react"

import { SetupStepHeader } from "@/components/Setup/SetupStepHeader"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  getSeedQuizWrongIndices,
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
  const [fillError, setFillError] = useState(false)
  const [wrongIndices, setWrongIndices] = useState<Set<number>>(() => new Set())

  const allFilled = positions.every((index) => answers[index]?.trim())

  const handleSubmit = () => {
    if (!allFilled) {
      setFillError(true)
      setWrongIndices(new Set())
      return
    }
    const wrong = getSeedQuizWrongIndices(words, positions, answers)
    if (wrong.length > 0) {
      setFillError(false)
      setWrongIndices(new Set(wrong))
      return
    }
    setFillError(false)
    setWrongIndices(new Set())
    onComplete()
  }

  const hasWrongAnswers = wrongIndices.size > 0

  return (
    <div className="flex flex-col gap-6">
      <SetupStepHeader
        step={step}
        total={total}
        title="Confirm your seed phrase"
        subtitle="Enter the missing words from your saved phrase."
      />
      <div className="flex flex-col gap-4">
        {positions.map((index) => {
          const fieldWrong = wrongIndices.has(index)
          const errorId = `seed-quiz-${index}-error`
          return (
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
                aria-invalid={fieldWrong || undefined}
                aria-describedby={fieldWrong ? errorId : undefined}
                value={answers[index] ?? ""}
                onChange={(event) => {
                  const value = event.target.value
                  setAnswers((prev) => ({
                    ...prev,
                    [index]: value,
                  }))
                  if (wrongIndices.has(index)) {
                    setWrongIndices((prev) => {
                      const next = new Set(prev)
                      next.delete(index)
                      return next
                    })
                  }
                  if (fillError) {
                    setFillError(false)
                  }
                }}
              />
              {fieldWrong && (
                <p
                  id={errorId}
                  className="text-sm text-destructive"
                  role="alert"
                >
                  Word #{index + 1} does not match
                </p>
              )}
            </div>
          )
        })}
      </div>
      {fillError && (
        <p className="text-sm text-destructive" role="alert">
          Fill in every word.
        </p>
      )}
      {hasWrongAnswers && (
        <p className="text-sm text-destructive" role="alert">
          One or more words do not match. Check your phrase and try again.
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
