import { useMemo, useState } from "react"

import { SetupStepHeader } from "@/components/Setup/SetupStepHeader"
import {
  SeedPhraseWordGrid,
  SeedPhraseWordGridCell,
  SeedPhraseWordGridSlot,
  seedPhraseQuizInputClassName,
} from "@/components/Wallet/SeedPhraseWordGrid"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { cn } from "@/lib/utils"
import { cryptoSecretInputProps } from "@/lib/crypto-secret-input"
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

  const applyBlurValidation = (index: number, rawValue: string) => {
    const result = getSeedQuizBlurResult(words[index] ?? "", rawValue)
    setAnswers((prev) => ({
      ...prev,
      [index]: rawValue,
    }))
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
              <SeedPhraseWordGridSlot
                key={`${index}-${word}`}
                cell={
                  <SeedPhraseWordGridCell index={index}>
                    <span className="truncate">{word}</span>
                  </SeedPhraseWordGridCell>
                }
              />
            )
          }

          const fieldWrong = wrongIndices.has(index)
          const isConfirmed = confirmedIndices.has(index)
          const errorId = `seed-quiz-${index}-error`

          if (isConfirmed) {
            return (
              <SeedPhraseWordGridSlot
                key={`${index}-confirmed`}
                cell={
                  <SeedPhraseWordGridCell
                    index={index}
                    className="border-frost/40 bg-frost/10"
                  >
                    <span className="truncate">{word}</span>
                  </SeedPhraseWordGridCell>
                }
              />
            )
          }

          return (
            <SeedPhraseWordGridSlot
              key={`${index}-input`}
              cell={
                <SeedPhraseWordGridCell
                  index={index}
                  className={cn(fieldWrong && "border-neg ring-1 ring-neg/20")}
                >
                  <Input
                    id={`seed-quiz-${index}`}
                    className={seedPhraseQuizInputClassName}
                    style={{
                      minWidth: `${BIP39_ENGLISH_MAX_WORD_LENGTH}ch`,
                    }}
                    {...cryptoSecretInputProps}
                    aria-invalid={fieldWrong || undefined}
                    aria-describedby={fieldWrong ? errorId : undefined}
                    value={answers[index] ?? ""}
                    onBlur={(event) => {
                      applyBlurValidation(index, event.target.value)
                    }}
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
              }
              footer={
                fieldWrong ? (
                  <p
                    id={errorId}
                    className="text-destructive"
                    role="alert"
                  >
                    Does not match
                  </p>
                ) : undefined
              }
            />
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
