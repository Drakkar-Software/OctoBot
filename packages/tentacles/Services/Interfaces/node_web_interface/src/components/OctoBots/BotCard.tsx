import { Check, Clock, Layers, Lock } from "lucide-react"
import { memo } from "react"

import type { Task_Output as Task, TaskStatus } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import { getActiveExecution, getStatusGroup, hasStartedExecution } from "@/utils/executions"
import { formatDate, formatElapsed, formatIsoTooltip, formatRelativeFuture, parseActionCount } from "@/utils/task-format"
import { getDisplayDate, getStatusVariant, statusLabels } from "@/utils/task-status"
import { BotAvatar } from "./BotAvatar"

function DateRow({ date }: { date: { label: string; value: string } | null }) {
  if (!date) return null
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-default">
          <Clock className="size-3.5 shrink-0" />
          {date.label}: {formatDate(date.value)}
        </span>
      </TooltipTrigger>
      <TooltipContent side="bottom">
        <span className="font-mono text-xs">{formatIsoTooltip(date.value)}</span>
      </TooltipContent>
    </Tooltip>
  )
}

function BotCardBody({ task, isRunning, isScheduled }: { task: Task; isRunning: boolean; isScheduled: boolean }) {
  const activeExec = getActiveExecution(task.executions)
  const group = getStatusGroup(activeExec?.status)
  const date = getDisplayDate(task)
  const runCount = task.executions?.length ?? 0
  const completedSteps = task.executions?.filter((e) => e.status === "completed" || e.status === "failed").length ?? 0
  const actionCount = parseActionCount(activeExec?.actions)

  if (group === "active") {
    if (isRunning) {
      const runningExec = task.executions?.find((e) => e.status === "running")
      const elapsedFrom = runningExec?.scheduled_at ?? activeExec?.scheduled_at
      return (
        <CardContent className="flex flex-col gap-2 pt-0">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            {activeExec?.type && (
              <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                {activeExec.type}
              </span>
            )}
            {runCount > 0 && (
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <Layers className="size-3.5" />
                {runCount} run{runCount !== 1 ? "s" : ""}
              </span>
            )}
            {completedSteps > 0 && (
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                {completedSteps} done
              </span>
            )}
            {elapsedFrom && (
              <span className="text-xs text-muted-foreground">
                Running {formatElapsed(elapsedFrom)}
              </span>
            )}
          </div>
          <DateRow date={date} />
        </CardContent>
      )
    }

    return (
      <CardContent className="flex flex-col gap-2 pt-0">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          {activeExec?.type && (
            <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
              {activeExec.type}
            </span>
          )}
          {actionCount != null && (
            <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
              {actionCount} action{actionCount !== 1 ? "s" : ""} queued
            </span>
          )}
        </div>
        {isScheduled && activeExec?.scheduled_at ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-default">
                <Clock className="size-3.5 shrink-0" />
                Next run: {formatRelativeFuture(activeExec.scheduled_at)}
              </span>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              <span className="font-mono text-xs">{formatIsoTooltip(activeExec.scheduled_at)}</span>
            </TooltipContent>
          </Tooltip>
        ) : (
          <DateRow date={date} />
        )}
      </CardContent>
    )
  }

  const isFailed = activeExec?.status === "failed"

  return (
    <CardContent className="flex flex-col gap-2 pt-0">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {activeExec?.type && (
          <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
            {activeExec.type}
          </span>
        )}
        {runCount > 0 && (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Layers className="size-3.5" />
            {runCount} run{runCount !== 1 ? "s" : ""}
          </span>
        )}
      </div>
      <div className={cn("text-xs", isFailed ? "text-destructive/80" : "text-muted-foreground")}>
        {date ? `${date.label}: ${formatDate(date.value)}` : null}
      </div>
    </CardContent>
  )
}

function areTaskPropsEqual(
  prev: { task: Task; selected: boolean },
  next: { task: Task; selected: boolean },
): boolean {
  return (
    prev.selected === next.selected &&
    prev.task.id === next.task.id &&
    prev.task.name === next.task.name &&
    prev.task.error === next.task.error &&
    prev.task.executions?.length === next.task.executions?.length &&
    JSON.stringify(prev.task.executions) === JSON.stringify(next.task.executions)
  )
}

export const BotCard = memo(function BotCard({
  task,
  selected,
  onToggleSelect,
}: {
  task: Task
  selected: boolean
  onToggleSelect: (id: string) => void
}) {
  const activeExec = getActiveExecution(task.executions)
  const rawStatus = (activeExec?.status ?? "scheduled") as TaskStatus
  const group = getStatusGroup(rawStatus)
  const hasError = !!task.error
  const started = hasStartedExecution(task.executions)

  const label = task.name || activeExec?.name || `OctoBot ${task.id?.slice(0, 6) || "new"}`
  const isEncrypted = task.is_encrypted ?? false

  let displayLabel: string
  let badgeStatus: TaskStatus
  if (hasError) {
    displayLabel = "Error"
    badgeStatus = "failed"
  } else if (group === "active") {
    if (rawStatus === "periodic") {
      displayLabel = "Recurring"
      badgeStatus = "periodic"
    } else if (started) {
      displayLabel = "Running"
      badgeStatus = "running"
    } else {
      displayLabel = "Scheduled"
      badgeStatus = "scheduled"
    }
  } else {
    displayLabel = statusLabels[rawStatus]
    badgeStatus = rawStatus
  }

  const isRunning = displayLabel === "Running"
  const isScheduled = displayLabel === "Scheduled"

  return (
    <Card
      className={cn(
        "relative cursor-pointer transition-all hover:shadow-md",
        selected
          ? "ring-2 ring-primary shadow-md"
          : "hover:ring-1 hover:ring-primary/40",
        hasError && !selected && "ring-1 ring-destructive",
      )}
      onClick={() => task.id && onToggleSelect(task.id)}
    >
      {selected && (
        <div className="absolute right-3 top-3 flex size-5 items-center justify-center rounded-full bg-primary">
          <Check className="size-3 text-primary-foreground" />
        </div>
      )}
      <CardHeader className="gap-1.5 pb-2">
        <div className="flex items-start gap-3">
          <BotAvatar isRunning={isRunning} />
          <div className="min-w-0 flex-1">
            <div className="grid grid-cols-[1fr_auto] items-start gap-2">
              <span className="flex items-center gap-1.5 truncate text-sm font-semibold leading-tight">
                <span className="truncate">{label}</span>
                {isEncrypted && <Lock className="size-3 shrink-0 text-muted-foreground/50" />}
              </span>
              <Badge
                variant={getStatusVariant(badgeStatus, hasError)}
                className={cn(selected && "mr-6", isScheduled && "animate-pulse")}
              >
                {displayLabel}
              </Badge>
            </div>
            <div className="mt-0.5 flex items-center justify-between gap-2 min-w-0">
              <span className="font-mono text-xs text-muted-foreground shrink-0">
                ID: {task.id?.slice(0, 12) || "—"}
              </span>
              {hasError && (
                <span className="font-mono text-xs text-red-400 truncate text-right">{task.error}</span>
              )}
            </div>
          </div>
        </div>
      </CardHeader>
      <BotCardBody task={task} isRunning={isRunning} isScheduled={isScheduled} />
    </Card>
  )
}, areTaskPropsEqual)
