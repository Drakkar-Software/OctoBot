import { useMemo, useState } from "react"

import { SetupStepHeader } from "@/components/Setup/SetupStepHeader"
import {
  SeedPhraseWordGrid,
  SeedPhraseWordGridCell,
} from "@/components/Wallet/SeedPhraseWordGrid"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  BIP39_ENGLISH_MAX_WORD_LENGTH,
  getSeedQuizBlurResult,
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
  const quizPositionSet = useMemo(() => new Set(positions), [positions])

  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [confirmedIndices, setConfirmedIndices] = useState<Set<number>>(
    () => new Set(),
  )
  const [wrongIndices, setWrongIndices] = useState<Set<number>>(() => new Set())

  const allConfirmed = positions.every((index) => confirmedIndices.has(index))

  const handleBlur = (index: number) => {
    const result = getSeedQuizBlurResult(words[index] ?? "", answers[index] ?? "")
    setWrongIndices((prev) => {
      const next = new Set(prev)
      if (result === "wrong") {
        next.add(index)
      } else {
        next.delete(index)
      }
      return next
    })
    setConfirmedIndices((prev) => {
      const next = new Set(prev)
      if (result === "correct") {
        next.add(index)
      } else {
        next.delete(index)
      }
      return next
    })
  }

  const handleSubmit = () => {
    if (allConfirmed) {
      onComplete()
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <SetupStepHeader
        step={step}
        total={total}
        title="Confirm your seed phrase"
        subtitle="Enter the missing words from your saved phrase."
      />
      <SeedPhraseWordGrid>
        {words.map((word, index) => {
          const isQuizCell = quizPositionSet.has(index)
          if (!isQuizCell) {
            return (
              <SeedPhraseWordGridCell key={`${index}-${word}`} index={index}>
                {word}
              </SeedPhraseWordGridCell>
            )
          }

          const fieldWrong = wrongIndices.has(index)
          const isConfirmed = confirmedIndices.has(index)
          const errorId = `seed-quiz-${index}-error`

          if (isConfirmed) {
            return (
              <SeedPhraseWordGridCell
                key={`${index}-confirmed`}
                index={index}
                className="border-frost/40 bg-frost/10"
              >
                {word}
              </SeedPhraseWordGridCell>
            )
          }

          return (
            <div key={`${index}-input`} className="flex flex-col gap-1">
              <SeedPhraseWordGridCell index={index} className="py-1.5">
                <Input
                  id={`seed-quiz-${index}`}
                  className="h-9 w-full min-w-0 rounded-md px-2 py-1 text-sm font-mono"
                  style={{
                    minWidth: `${BIP39_ENGLISH_MAX_WORD_LENGTH}ch`,
                  }}
                  autoComplete="off"
                  aria-invalid={fieldWrong || undefined}
                  aria-describedby={fieldWrong ? errorId : undefined}
                  value={answers[index] ?? ""}
                  onBlur={() => handleBlur(index)}
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
                  }}
                />
              </SeedPhraseWordGridCell>
              {fieldWrong && (
                <p
                  id={errorId}
                  className="text-sm text-destructive"
                  role="alert"
                >
                  Does not match
                </p>
              )}
            </div>
          )
        })}
      </SeedPhraseWordGrid>
      <div className="flex flex-col gap-2 sm:flex-row sm:justify-between">
        <Button type="button" variant="outline" onClick={onPrevious}>
          Previous
        </Button>
        <LoadingButton
          type="button"
          disabled={!allConfirmed}
          onClick={handleSubmit}
        >
          Continue
        </LoadingButton>
      </div>
    </div>
  )
}
