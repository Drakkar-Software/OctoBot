import "fake-indexeddb/auto"
import { beforeEach, describe, expect, it, vi } from "vitest"

import {
  clearClientStorageWithoutReload,
  resetClientStorage,
} from "@/lib/client-storage-reset"
import { DEVICE_DATABASE_NAME } from "@/lib/ui-recovery-constants"

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

vi.stubGlobal("localStorage", localStorageMock)
vi.stubGlobal("sessionStorage", sessionStorageMock)

const mocks = vi.hoisted(() => ({
  reportUiJournalEvent: vi.fn().mockResolvedValue(undefined),
  reloadMock: vi.fn(),
}))

vi.mock("@/lib/journal-client-event", () => ({
  reportUiJournalEvent: mocks.reportUiJournalEvent,
}))

describe("client-storage-reset", () => {
  beforeEach(() => {
    localStorageMock.setItem("auth_username", "wallet")
    sessionStorageMock.setItem("octobot_client_instance_id", "client-1")
    mocks.reportUiJournalEvent.mockClear()
    mocks.reloadMock.mockClear()
    vi.stubGlobal("window", {
      location: { reload: mocks.reloadMock },
    })
  })

  async function openDeviceDatabase(): Promise<IDBDatabase> {
    return await new Promise((resolve, reject) => {
      const openRequest = indexedDB.open(DEVICE_DATABASE_NAME, 1)
      openRequest.onupgradeneeded = () => {
        openRequest.result.createObjectStore("secure_storage")
      }
      openRequest.onsuccess = () => resolve(openRequest.result)
      openRequest.onerror = () => reject(openRequest.error)
    })
  }

  async function writeDeviceRecord(value: string): Promise<void> {
    const database = await openDeviceDatabase()
    await new Promise<void>((resolve, reject) => {
      const transaction = database.transaction("secure_storage", "readwrite")
      const putRequest = transaction
        .objectStore("secure_storage")
        .put(value, "password")
      putRequest.onsuccess = () => {
        database.close()
        resolve()
      }
      putRequest.onerror = () => reject(putRequest.error)
    })
  }

  async function readDeviceRecord(): Promise<unknown> {
    const database = await openDeviceDatabase()
    return await new Promise((resolve, reject) => {
      const transaction = database.transaction("secure_storage", "readonly")
      const getRequest = transaction.objectStore("secure_storage").get("password")
      getRequest.onsuccess = () => {
        database.close()
        resolve(getRequest.result)
      }
      getRequest.onerror = () => reject(getRequest.error)
    })
  }

  it("does not reset on module import", () => {
    expect(mocks.reportUiJournalEvent).not.toHaveBeenCalled()
    expect(mocks.reloadMock).not.toHaveBeenCalled()
  })

  it("performs a full reset and journals before reload", async () => {
    await writeDeviceRecord("secret")
    expect(await readDeviceRecord()).toBe("secret")

    await resetClientStorage("manual_recovery")

    expect(mocks.reportUiJournalEvent.mock.invocationCallOrder[0]).toBeLessThan(
      mocks.reloadMock.mock.invocationCallOrder[0],
    )
    expect(mocks.reportUiJournalEvent).toHaveBeenCalledWith(
      "ui_client_storage_reset",
      {
        reset_tier: "full",
        trigger: "manual_recovery",
        recovery_attempt: 1,
      },
      { allowDuplicate: true },
    )
    expect(localStorageMock.length).toBe(0)
    expect(sessionStorageMock.length).toBe(0)
    expect(await readDeviceRecord()).toBeUndefined()
    expect(mocks.reloadMock).toHaveBeenCalledOnce()
  })

  it("clears storage without reload for static recovery", async () => {
    await writeDeviceRecord("secret")

    await clearClientStorageWithoutReload()

    expect(localStorageMock.length).toBe(0)
    expect(sessionStorageMock.length).toBe(0)
    expect(await readDeviceRecord()).toBeUndefined()
    expect(mocks.reloadMock).not.toHaveBeenCalled()
  })
})
