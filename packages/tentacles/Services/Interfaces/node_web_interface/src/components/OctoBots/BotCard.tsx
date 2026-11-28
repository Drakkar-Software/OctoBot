import { ArrowUpRight, Check, Clock, Layers, Lock, TriangleAlert } from "lucide-react"
import { memo } from "react"

import { OpenAPI } from "@/client"
import type {
  ChildOctoBotProcessState,
  Execution,
  Task,
  TaskStatus,
} from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { buildMobileUiBotUrl } from "@/lib/mobile-ui"
import { cn } from "@/lib/utils"
import {
  getActiveExecution,
  getStatusGroup,
  hasStartedExecution,
} from "@/utils/executions"
import { buildProcessBotUrl, formatProcessAddress } from "@/utils/process-address"
import { resolveTaskError, type TaskErrorInfo } from "@/utils/task-errors"
import {
  formatDate,
  formatElapsed,
  formatIsoTooltip,
  parseActionCount,
} from "@/utils/task-format"
import {
  getDisplayDate,
  getStatusVariant,
  isTaskCancelled,
  statusLabels,
} from "@/utils/task-status"
import { BotAvatar } from "./BotAvatar"

function AutomationTitleOpenLink({
  label,
  automationId,
  browserAppReady,
  isEncrypted,
  showBrowserAppTitleOpen,
}: {
  label: string
  automationId: string
  browserAppReady: boolean
  isEncrypted: boolean
  showBrowserAppTitleOpen: boolean
}) {
  const href = buildMobileUiBotUrl(
    OpenAPI.BASE,
    window.location.origin,
    automationId,
  )
  const stopOpen = (event: React.MouseEvent) => event.stopPropagation()

  return (
    <span className="flex min-w-0 items-center gap-1.5">
      {showBrowserAppTitleOpen && browserAppReady ? (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`View in browser app: ${label}`}
          onClick={stopOpen}
          className="group flex min-w-0 items-center gap-0.5 rounded-sm text-foreground transition-colors hover:text-primary"
        >
          <span className="truncate">{label}</span>
          <ArrowUpRight
            className="size-4 shrink-0 text-muted-foreground transition-colors group-hover:text-primary"
            aria-hidden
          />
        </a>
      ) : (
        <span className="flex min-w-0 items-center gap-0.5">
          <span className="truncate">{label}</span>
          {showBrowserAppTitleOpen ? (
            <span
              className="invisible flex size-4 shrink-0 items-center justify-center"
              aria-hidden
            >
              <ArrowUpRight className="size-4" />
            </span>
          ) : null}
        </span>
      )}
      {isEncrypted ? (
        <Lock className="size-3 shrink-0 text-muted-foreground/50" />
      ) : null}
    </span>
  )
}

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
        <span className="font-mono text-xs">
          {formatIsoTooltip(date.value)}
        </span>
      </TooltipContent>
    </Tooltip>
  )
}

function ErrorPanel({ status, message }: TaskErrorInfo) {
  const full = [status, message].filter(Boolean).join(": ")
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div className="flex items-start gap-2 rounded-md border border-neg/25 border-l-2 border-l-neg/70 bg-neg/[0.07] px-2.5 py-1.5 cursor-default">
          <TriangleAlert className="mt-0.5 size-3.5 shrink-0 text-neg/80" />
          <div className="min-w-0 flex-1">
            {status && (
              <div className="truncate font-mono text-[11px] font-medium leading-tight text-neg">
                {status}
              </div>
            )}
            {message && (
              <div
                className={cn(
                  "text-xs leading-snug text-neg/75 line-clamp-2",
                  status && "mt-0.5",
                )}
              >
                {message}
              </div>
            )}
          </div>
        </div>
      </TooltipTrigger>
      <TooltipContent side="bottom" className="max-w-sm">
        <span className="block whitespace-pre-wrap break-words font-mono text-xs">
          {full}
        </span>
      </TooltipContent>
    </Tooltip>
  )
}

function ProcessAddressRow({
  childProcess,
}: {
  childProcess: ChildOctoBotProcessState
}) {
  const processBotUrl = buildProcessBotUrl(childProcess.web_port)
  const processAddress = formatProcessAddress(childProcess)

  return (
    <div className="flex min-w-0 items-center gap-1">
      <a
        href={processBotUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="min-w-0 truncate font-mono text-xs text-primary hover:underline"
        onClick={(event) => event.stopPropagation()}
      >
        {processAddress}
      </a>
      <Button
        variant="ghost"
        size="icon"
        className="size-7 shrink-0 text-primary"
        asChild
      >
        <a
          href={processBotUrl}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Open child OctoBot at ${processAddress}`}
          onClick={(event) => event.stopPropagation()}
        >
          <ArrowUpRight className="size-4" />
        </a>
      </Button>
    </div>
  )
}

function RunsCounterRow({
  task,
  isRunning,
}: {
  task: Task
  isRunning: boolean
}) {
  const activeExec = getActiveExecution(task.executions)
  const runCount = task.executions?.length ?? 0
  const completedSteps =
    task.executions?.filter(
      (execution: Execution) =>
        execution.status === "completed" || execution.status === "failed",
    ).length ?? 0
  const runningExec = task.executions?.find(
    (execution: Execution) => execution.status === "running",
  )
  const elapsedFrom = runningExec?.scheduled_at ?? activeExec?.scheduled_at

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
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
      {isRunning && elapsedFrom && (
        <span className="text-xs text-muted-foreground">
          Running {formatElapsed(elapsedFrom)}
        </span>
      )}
    </div>
  )
}

function BotCardBody({
  task,
  isRunning,
  isScheduled,
  errorInfo,
}: {
  task: Task
  isRunning: boolean
  isScheduled: boolean
  errorInfo: TaskErrorInfo | null
}) {
  const activeExec = getActiveExecution(task.executions)
  const group = getStatusGroup(activeExec?.status)
  const date = getDisplayDate(task)
  const actionCount = parseActionCount(activeExec?.actions)
  const childProcess = task.metadata?.child_octobot_process ?? null

  const errorPanel =
    errorInfo && (errorInfo.status || errorInfo.message) ? (
      <ErrorPanel status={errorInfo.status} message={errorInfo.message} />
    ) : null

  if (group === "active") {
    if (isRunning) {
      return (
        <CardContent className="flex flex-col gap-2 pt-0 -mt-4">
          {errorPanel}
          {childProcess ? (
            <ProcessAddressRow childProcess={childProcess} />
          ) : (
            <RunsCounterRow task={task} isRunning={isRunning} />
          )}
          <DateRow date={date} />
        </CardContent>
      )
    }

    return (
      <CardContent className="flex flex-col gap-2 pt-0 -mt-4">
        {errorPanel}
        {childProcess ? (
          <ProcessAddressRow childProcess={childProcess} />
        ) : (
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            {actionCount != null && (
              <span className="rounded bg-surface-mid px-2 py-0.5 text-xs font-medium text-muted-foreground">
                {actionCount} action{actionCount !== 1 ? "s" : ""} queued
              </span>
            )}
          </div>
        )}
        {isScheduled && activeExec?.scheduled_at ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-default">
                <Clock className="size-3.5 shrink-0" />
                Next run: {formatDate(activeExec.scheduled_at)}
              </span>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              <span className="font-mono text-xs">
                {formatIsoTooltip(activeExec.scheduled_at)}
              </span>
            </TooltipContent>
          </Tooltip>
        ) : (
          <DateRow date={date} />
        )}
      </CardContent>
    )
  }

  return (
    <CardContent className="flex flex-col gap-2 pt-0 -mt-4">
      {errorPanel}
      {childProcess ? (
        <ProcessAddressRow childProcess={childProcess} />
      ) : (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          {(task.executions?.length ?? 0) > 0 && (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <Layers className="size-3.5" />
              {task.executions?.length} run
              {(task.executions?.length ?? 0) !== 1 ? "s" : ""}
            </span>
          )}
          <DateRow date={date} />
        </div>
      )}
      {childProcess && <DateRow date={date} />}
    </CardContent>
  )
}

function areTaskPropsEqual(
  prev: { task: Task; selected: boolean; browserAppReady: boolean },
  next: { task: Task; selected: boolean; browserAppReady: boolean },
): boolean {
  return (
    prev.selected === next.selected &&
    prev.browserAppReady === next.browserAppReady &&
    prev.task.id === next.task.id &&
    prev.task.name === next.task.name &&
    prev.task.error === next.task.error &&
    prev.task.error_message === next.task.error_message &&
    prev.task.executions?.length === next.task.executions?.length &&
    JSON.stringify(prev.task.executions) ===
      JSON.stringify(next.task.executions) &&
    JSON.stringify(prev.task.metadata?.child_octobot_process) ===
      JSON.stringify(next.task.metadata?.child_octobot_process)
  )
}

export const BotCard = memo(function BotCard({
  task,
  selected,
  browserAppReady,
  onToggleSelect,
}: {
  task: Task
  selected: boolean
  browserAppReady: boolean
  onToggleSelect: (id: string) => void
}) {
  const activeExec = getActiveExecution(task.executions)
  const rawStatus = (activeExec?.status ?? "scheduled") as TaskStatus
  const group = getStatusGroup(rawStatus)
  const hasError = !!task.error && !isTaskCancelled(task)
  const errorInfo = hasError ? resolveTaskError(task) : null
  const started = hasStartedExecution(task.executions)

  const label =
    task.name || activeExec?.name || `OctoBot ${task.id?.slice(0, 6) || "new"}`
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
  const showBrowserAppTitleOpen = Boolean(task.id)

  return (
    <Card
      className={cn(
        "relative cursor-pointer transition-all",
        selected
          ? "ring-2 ring-primary shadow-glow"
          : "hover:ring-1 hover:ring-frost/50 hover:border-frost/40",
        hasError && !selected && "ring-1 ring-neg",
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
              <div className="min-w-0 text-sm font-semibold leading-tight">
                {showBrowserAppTitleOpen && task.id ? (
                  <AutomationTitleOpenLink
                    label={label}
                    automationId={task.id}
                    browserAppReady={browserAppReady}
                    isEncrypted={isEncrypted}
                    showBrowserAppTitleOpen
                  />
                ) : (
                  <span className="flex items-center gap-1.5 truncate">
                    <span className="truncate">{label}</span>
                    {isEncrypted ? (
                      <Lock className="size-3 shrink-0 text-muted-foreground/50" />
                    ) : null}
                  </span>
                )}
              </div>
              <Badge
                variant={getStatusVariant(badgeStatus, hasError)}
                className={cn(
                  selected && "mr-6",
                  isScheduled && "animate-pulse",
                )}
              >
                {displayLabel}
              </Badge>
            </div>
            <div className="mt-0.5 min-w-0">
              <span className="font-mono text-xs text-muted-foreground">
                ID: {task.id?.slice(0, 12) || "-"}
              </span>
            </div>
          </div>
        </div>
      </CardHeader>
      <BotCardBody
        task={task}
        isRunning={isRunning}
        isScheduled={isScheduled}
        errorInfo={errorInfo}
      />
    </Card>
  )
}, areTaskPropsEqual)
