import { Bot } from "lucide-react"
import { memo, useState } from "react"

const RING_RADIUS = 22
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS

export const BotAvatar = memo(function BotAvatar({
  isRunning,
}: {
  isRunning: boolean
}) {
  const [animOffset] = useState(() => `-${(Math.random() * 3).toFixed(2)}s`)

  return (
    <div className="relative flex size-12 shrink-0 items-center justify-center">
      {isRunning && (
        <>
          <svg
            className="absolute inset-0 size-full"
            viewBox="0 0 48 48"
            aria-hidden
          >
            <circle
              cx="24"
              cy="24"
              r={RING_RADIUS}
              fill="none"
              className="stroke-muted-foreground/20"
              strokeWidth="2"
            />
          </svg>
          <svg
            className="absolute inset-0 size-full animate-spin"
            style={{ animationDuration: "3s", animationDelay: animOffset }}
            viewBox="0 0 48 48"
            aria-hidden
          >
            <circle
              cx="24"
              cy="24"
              r={RING_RADIUS}
              fill="none"
              className="stroke-primary"
              strokeWidth="2"
              strokeLinecap="round"
              strokeDasharray={`${RING_CIRCUMFERENCE * 0.15} ${RING_CIRCUMFERENCE}`}
            />
          </svg>
        </>
      )}
      <div className="flex size-10 items-center justify-center rounded-full bg-surface-mid">
        <Bot className="size-5 text-frost" />
      </div>
    </div>
  )
})
