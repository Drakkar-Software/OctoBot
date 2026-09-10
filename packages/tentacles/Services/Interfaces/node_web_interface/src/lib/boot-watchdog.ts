import {
  BOOT_FAILED_FLAG,
  BOOT_SUCCEEDED_FLAG,
  BOOT_TIMEOUT_MS,
  RECOVERY_EXPLANATION,
  RESET_CONFIRM_MESSAGE,
  SESSION_HEARTBEAT_KEY,
  SESSION_HEARTBEAT_STALE_MS,
  SESSION_ID_KEY,
} from "@/lib/ui-recovery-constants"

const STATIC_RECOVERY_PANEL_ID = "octobot-static-recovery-panel"

type WindowWithBootFlags = Window &
  typeof globalThis & {
    [BOOT_FAILED_FLAG]?: boolean
    [BOOT_SUCCEEDED_FLAG]?: boolean
  }

function getBootWindow(): WindowWithBootFlags {
  return window as WindowWithBootFlags
}

export function markBootFailed(): void {
  getBootWindow()[BOOT_FAILED_FLAG] = true
}

export function markBootSucceeded(): void {
  const bootWindow = getBootWindow()
  bootWindow[BOOT_SUCCEEDED_FLAG] = true
  bootWindow[BOOT_FAILED_FLAG] = false
  hideStaticRecoveryPanel()
}

export function isBootFailed(): boolean {
  return getBootWindow()[BOOT_FAILED_FLAG] === true
}

export function isBootSucceeded(): boolean {
  return getBootWindow()[BOOT_SUCCEEDED_FLAG] === true
}

export function touchSessionHeartbeat(now = Date.now()): void {
  sessionStorage.setItem(SESSION_HEARTBEAT_KEY, String(now))
  if (!sessionStorage.getItem(SESSION_ID_KEY)) {
    sessionStorage.setItem(SESSION_ID_KEY, createSessionId())
  }
}

export function getPriorSessionId(): string | null {
  return sessionStorage.getItem(SESSION_ID_KEY)
}

export function shouldReportSessionAborted(): boolean {
  return priorSessionWasAborted && isBootFailed()
}

function createSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID()
  }
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function hideStaticRecoveryPanel(): void {
  const panel = document.getElementById(STATIC_RECOVERY_PANEL_ID)
  if (panel) {
    panel.style.display = "none"
  }
}

export function showStaticRecoveryPanel(): void {
  let panel = document.getElementById(STATIC_RECOVERY_PANEL_ID)
  if (!panel) {
    panel = document.createElement("div")
    panel.id = STATIC_RECOVERY_PANEL_ID
    panel.innerHTML = `
      <div style="max-width:32rem;margin:2rem auto;padding:1.5rem;border:1px solid #444;border-radius:0.5rem;font-family:system-ui,sans-serif;">
        <h1 style="font-size:1.25rem;margin:0 0 0.75rem;">OctoBot Node recovery</h1>
        <p style="margin:0 0 1rem;line-height:1.5;">${RECOVERY_EXPLANATION}</p>
        <button type="button" id="octobot-static-recovery-reset" style="padding:0.5rem 1rem;cursor:pointer;">
          Reset local browser data
        </button>
      </div>
    `
    document.body.appendChild(panel)
    const resetButton = panel.querySelector("#octobot-static-recovery-reset")
    resetButton?.addEventListener("click", () => {
      if (!window.confirm(RESET_CONFIRM_MESSAGE)) {
        return
      }
      getBootWindow().dispatchEvent(
        new CustomEvent("octobot-static-recovery-reset-requested"),
      )
    })
  }
  panel.style.display = "block"
}

let bootTimeoutId: ReturnType<typeof setTimeout> | null = null
let priorSessionWasAborted = false

export function wasPriorSessionAborted(): boolean {
  return priorSessionWasAborted
}

export function readPriorSessionAborted(now = Date.now()): boolean {
  const priorHeartbeatRaw = sessionStorage.getItem(SESSION_HEARTBEAT_KEY)
  if (!priorHeartbeatRaw) {
    return false
  }
  const priorHeartbeat = Number(priorHeartbeatRaw)
  if (Number.isNaN(priorHeartbeat)) {
    return true
  }
  return now - priorHeartbeat > SESSION_HEARTBEAT_STALE_MS
}

export function startBootWatchdog(options?: {
  onBootTimeout?: () => void
}): void {
  priorSessionWasAborted = readPriorSessionAborted()
  touchSessionHeartbeat()
  if (bootTimeoutId !== null) {
    clearTimeout(bootTimeoutId)
  }
  bootTimeoutId = setTimeout(() => {
    const rootElement = document.getElementById("root")
    const rootIsEmpty = !rootElement || rootElement.childElementCount === 0
    if (!rootIsEmpty || isBootSucceeded()) {
      return
    }
    markBootFailed()
    showStaticRecoveryPanel()
    options?.onBootTimeout?.()
  }, BOOT_TIMEOUT_MS)

  const refreshHeartbeat = () => touchSessionHeartbeat()
  document.addEventListener("visibilitychange", refreshHeartbeat)
  window.addEventListener("pagehide", refreshHeartbeat)
  window.setInterval(refreshHeartbeat, 5_000)
}
