import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

const sessionStorageStore: Record<string, string> = {}
const sessionStorageMock = {
  getItem: (key: string) => sessionStorageStore[key] ?? null,
  setItem: (key: string, value: string) => {
    sessionStorageStore[key] = value
  },
  removeItem: (key: string) => {
    delete sessionStorageStore[key]
  },
  clear: () => {
    Object.keys(sessionStorageStore).forEach((key) => {
      delete sessionStorageStore[key]
    })
  },
  get length() {
    return Object.keys(sessionStorageStore).length
  },
}

const localStorageStore: Record<string, string> = {}
const localStorageMock = {
  getItem: (key: string) => localStorageStore[key] ?? null,
  setItem: (key: string, value: string) => {
    localStorageStore[key] = value
  },
  removeItem: (key: string) => {
    delete localStorageStore[key]
  },
  clear: () => {
    Object.keys(localStorageStore).forEach((key) => {
      delete localStorageStore[key]
    })
  },
  get length() {
    return Object.keys(localStorageStore).length
  },
}

vi.stubGlobal("localStorage", localStorageMock)

vi.stubGlobal("sessionStorage", sessionStorageMock)

const windowListeners = new Map<string, Set<EventListener>>()
const windowMock = {
  addEventListener(type: string, listener: EventListener) {
    const listeners = windowListeners.get(type) ?? new Set<EventListener>()
    listeners.add(listener)
    windowListeners.set(type, listeners)
  },
  removeEventListener(type: string, listener: EventListener) {
    windowListeners.get(type)?.delete(listener)
  },
  dispatchEvent(event: Event) {
    windowListeners.get(event.type)?.forEach((listener) => {
      listener(event)
    })
    return true
  },
  confirm: vi.fn(),
  setInterval: vi.fn(() => 1),
  [BOOT_FAILED_FLAG]: false,
  [BOOT_SUCCEEDED_FLAG]: false,
} as BootWindow & {
  addEventListener: (type: string, listener: EventListener) => void
  removeEventListener: (type: string, listener: EventListener) => void
  dispatchEvent: (event: Event) => boolean
  confirm: ReturnType<typeof vi.fn>
  setInterval: ReturnType<typeof vi.fn>
}

vi.stubGlobal("window", windowMock)

class TestDomEvent {
  type: string
  bubbles: boolean
  constructor(type: string, init?: { bubbles?: boolean }) {
    this.type = type
    this.bubbles = init?.bubbles ?? false
  }
}

vi.stubGlobal("Event", TestDomEvent)
vi.stubGlobal("CustomEvent", TestDomEvent)
vi.stubGlobal("MouseEvent", TestDomEvent)

import {
  BOOT_FAILED_FLAG,
  BOOT_SUCCEEDED_FLAG,
  BOOT_TIMEOUT_MS,
  SESSION_HEARTBEAT_KEY,
  SESSION_HEARTBEAT_STALE_MS,
} from "@/lib/ui-recovery-constants"
import {
  isBootFailed,
  isBootSucceeded,
  markBootFailed,
  markBootSucceeded,
  readPriorSessionAborted,
  shouldReportSessionAborted,
  showStaticRecoveryPanel,
  startBootWatchdog,
  wasPriorSessionAborted,
} from "@/lib/boot-watchdog"

type BootWindow = Window & {
  [BOOT_FAILED_FLAG]?: boolean
  [BOOT_SUCCEEDED_FLAG]?: boolean
}

type TestElement = {
  id: string
  innerHTML: string
  style: { display: string }
  childElementCount: number
  appendChild: (child: TestElement) => void
  querySelector: (selector: string) => TestElement | null
  addEventListener: (
    type: string,
    listener: EventListenerOrEventListenerObject,
  ) => void
  dispatchEvent: (event: Event) => boolean
}

function createTestElement(id = ""): TestElement {
  const listeners = new Map<string, EventListenerOrEventListenerObject>()
  const children: TestElement[] = []
  return {
    id,
    innerHTML: "",
    style: { display: "block" },
    childElementCount: 0,
    appendChild(child: TestElement) {
      children.push(child)
      this.childElementCount = children.length
    },
    querySelector(selector: string) {
      if (selector === `#${id}` && id) {
        return this
      }
      for (const child of children) {
        if (selector === `#${child.id}`) {
          return child
        }
        const nestedMatch = child.querySelector(selector)
        if (nestedMatch) {
          return nestedMatch
        }
      }
      return null
    },
    addEventListener(type: string, listener: EventListenerOrEventListenerObject) {
      listeners.set(type, listener)
    },
    dispatchEvent(event: Event) {
      const listener = listeners.get(event.type)
      if (!listener) {
        return false
      }
      if (typeof listener === "function") {
        listener(event)
      } else {
        listener.handleEvent(event)
      }
      return true
    },
  }
}

describe("boot-watchdog", () => {
  let rootElement: TestElement
  let recoveryPanel: TestElement | null
  let resetButton: TestElement | null
  const bodyChildren: TestElement[] = []

  beforeEach(() => {
    vi.useFakeTimers()
    sessionStorageMock.clear()
    recoveryPanel = null
    resetButton = null
    bodyChildren.length = 0
    rootElement = createTestElement("root")

    vi.stubGlobal("document", {
      body: {
        appendChild: (element: TestElement) => {
          bodyChildren.push(element)
        },
      },
      getElementById: (elementId: string) => {
        if (elementId === "root") {
          return rootElement
        }
        if (elementId === "octobot-static-recovery-panel") {
          return recoveryPanel
        }
        if (elementId === "octobot-static-recovery-reset") {
          return resetButton
        }
        return null
      },
      createElement: (tagName: string) => {
        if (tagName === "div") {
          recoveryPanel = createTestElement("octobot-static-recovery-panel")
          resetButton = createTestElement("octobot-static-recovery-reset")
          recoveryPanel.appendChild(resetButton)
          return recoveryPanel
        }
        return createTestElement()
      },
      addEventListener: vi.fn(),
    })

    windowMock[BOOT_FAILED_FLAG] = false
    windowMock[BOOT_SUCCEEDED_FLAG] = false
    windowListeners.clear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("records stale prior sessions before refreshing heartbeat", () => {
    const staleHeartbeat = Date.now() - SESSION_HEARTBEAT_STALE_MS - 1
    sessionStorageMock.setItem(SESSION_HEARTBEAT_KEY, String(staleHeartbeat))

    startBootWatchdog()

    expect(wasPriorSessionAborted()).toBe(true)
    expect(readPriorSessionAborted()).toBe(false)
  })

  it("marks boot failed and shows static recovery without auto reset", () => {
    const onBootTimeout = vi.fn()
    startBootWatchdog({ onBootTimeout })

    vi.advanceTimersByTime(BOOT_TIMEOUT_MS)

    expect(isBootFailed()).toBe(true)
    expect(recoveryPanel).toBeTruthy()
    expect(onBootTimeout).toHaveBeenCalledOnce()
    expect(localStorageMock.length).toBe(0)
    expect(sessionStorageMock.getItem(SESSION_HEARTBEAT_KEY)).toBeTruthy()
  })

  it("does not flag boot failure after a successful mount", () => {
    startBootWatchdog()
    markBootSucceeded()
    rootElement.appendChild(createTestElement("child"))

    vi.advanceTimersByTime(BOOT_TIMEOUT_MS)

    expect(isBootSucceeded()).toBe(true)
    expect(isBootFailed()).toBe(false)
  })

  it("reports session aborted only when prior session was stale and boot failed", () => {
    const staleHeartbeat = Date.now() - SESSION_HEARTBEAT_STALE_MS - 1
    sessionStorageMock.setItem(SESSION_HEARTBEAT_KEY, String(staleHeartbeat))
    startBootWatchdog()
    expect(shouldReportSessionAborted()).toBe(false)

    markBootFailed()
    expect(shouldReportSessionAborted()).toBe(true)
  })

  it("dispatches a reset request only after static confirm", () => {
    const resetRequested = vi.fn()
    windowMock.addEventListener(
      "octobot-static-recovery-reset-requested",
      resetRequested,
    )
    windowMock.confirm.mockReturnValue(false)

    showStaticRecoveryPanel()
    resetButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }))

    expect(resetRequested).not.toHaveBeenCalled()

    windowMock.confirm.mockReturnValue(true)
    resetButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }))
    expect(resetRequested).toHaveBeenCalledOnce()

    windowMock.removeEventListener(
      "octobot-static-recovery-reset-requested",
      resetRequested,
    )
  })
})
