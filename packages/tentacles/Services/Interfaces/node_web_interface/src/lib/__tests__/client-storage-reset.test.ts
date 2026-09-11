import "fake-indexeddb/auto"
import { beforeEach, describe, expect, it, vi } from "vitest"

import {
  clearClientStorageWithoutReload,
  resetClientStorage,
} from "@/lib/client-storage-reset"
import { DEVICE_DATABASE_NAME } from "@/lib/ui-recovery-constants"

const ACTIVE_WALLET = "0xaaaa000000000000000000000000000000000001"
const OTHER_WALLET = "0xbbbb000000000000000000000000000000000002"

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
  key: (index: number) => Object.keys(localStorageStore)[index] ?? null,
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
    localStorageMock.clear()
    sessionStorageMock.clear()
    localStorageMock.setItem("auth_username", ACTIVE_WALLET)
    localStorageMock.setItem("auth_wallet_name", "Main wallet")
    localStorageMock.setItem("user_meta_templates", "[]")
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

  async function writeIdbRecord(recordKey: string, value: string): Promise<void> {
    const database = await openDeviceDatabase()
    await new Promise<void>((resolve, reject) => {
      const transaction = database.transaction("secure_storage", "readwrite")
      const putRequest = transaction
        .objectStore("secure_storage")
        .put(value, recordKey)
      putRequest.onsuccess = () => {
        database.close()
        resolve()
      }
      putRequest.onerror = () => reject(putRequest.error)
    })
  }

  async function readIdbRecord(recordKey: string): Promise<unknown> {
    const database = await openDeviceDatabase()
    return await new Promise((resolve, reject) => {
      const transaction = database.transaction("secure_storage", "readonly")
      const getRequest = transaction.objectStore("secure_storage").get(recordKey)
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

  it("clears all localStorage including auth and reloads", async () => {
    await resetClientStorage("manual_recovery")

    expect(localStorageMock.getItem("auth_username")).toBeNull()
    expect(localStorageMock.getItem("auth_wallet_name")).toBeNull()
    expect(localStorageMock.getItem("user_meta_templates")).toBeNull()
    expect(sessionStorageMock.length).toBe(0)
    expect(mocks.reloadMock).toHaveBeenCalledOnce()
  })

  it("journals with auth_preserved false before reload", async () => {
    await resetClientStorage("manual_settings")

    expect(mocks.reportUiJournalEvent.mock.invocationCallOrder[0]).toBeLessThan(
      mocks.reloadMock.mock.invocationCallOrder[0],
    )
    expect(mocks.reportUiJournalEvent).toHaveBeenCalledWith(
      "ui_client_storage_reset",
      {
        reset_tier: "full",
        auth_preserved: false,
        trigger: "manual_settings",
        recovery_attempt: 1,
      },
      { allowDuplicate: true },
    )
  })

  it("clears all IDB records including auth", async () => {
    await writeIdbRecord("device_key", "device-key")
    await writeIdbRecord("auth_password", "password")
    await writeIdbRecord("octochat_device_keys", "octochat")
    await writeIdbRecord(`client_keys:${ACTIVE_WALLET.toLowerCase()}`, "active")
    await writeIdbRecord(`client_keys:${OTHER_WALLET.toLowerCase()}`, "stale")
    await writeIdbRecord("orphan_record", "delete-me")

    await clearClientStorageWithoutReload()

    expect(await readIdbRecord("device_key")).toBeUndefined()
    expect(await readIdbRecord("auth_password")).toBeUndefined()
    expect(await readIdbRecord("octochat_device_keys")).toBeUndefined()
    expect(
      await readIdbRecord(`client_keys:${ACTIVE_WALLET.toLowerCase()}`),
    ).toBeUndefined()
    expect(
      await readIdbRecord(`client_keys:${OTHER_WALLET.toLowerCase()}`),
    ).toBeUndefined()
    expect(await readIdbRecord("orphan_record")).toBeUndefined()
  })

  it("clears storage without reload for static recovery", async () => {
    await writeIdbRecord("orphan_record", "delete-me")

    await clearClientStorageWithoutReload()

    expect(localStorageMock.getItem("auth_username")).toBeNull()
    expect(sessionStorageMock.length).toBe(0)
    expect(await readIdbRecord("orphan_record")).toBeUndefined()
    expect(mocks.reloadMock).not.toHaveBeenCalled()
  })
})
