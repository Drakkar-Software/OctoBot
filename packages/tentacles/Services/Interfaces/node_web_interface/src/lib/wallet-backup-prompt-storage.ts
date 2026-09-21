import { DEVICE_DATABASE_NAME } from "@/lib/ui-recovery-constants"

const STORE_NAME = "secure_storage"
const SETUP_SUCCEEDED_AT_RECORD = "wallet_setup_succeeded_at_ms"
const BACKUP_SAVED_ACK_RECORD = "wallet_backup_saved_ack"

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DEVICE_DATABASE_NAME, 1)
    req.onupgradeneeded = () => {
      req.result.createObjectStore(STORE_NAME)
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function readRecord(key: string): Promise<string | null> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const req = db.transaction(STORE_NAME, "readonly").objectStore(STORE_NAME).get(key)
    req.onsuccess = () => {
      const value = req.result
      resolve(typeof value === "string" ? value : null)
    }
    req.onerror = () => reject(req.error)
  })
}

async function writeRecord(key: string, value: string): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const req = db
      .transaction(STORE_NAME, "readwrite")
      .objectStore(STORE_NAME)
      .put(value, key)
    req.onsuccess = () => resolve()
    req.onerror = () => reject(req.error)
  })
}

export async function loadLocalWalletSetupSucceededAtMs(): Promise<number | null> {
  const raw = await readRecord(SETUP_SUCCEEDED_AT_RECORD)
  if (!raw) {
    return null
  }
  const parsed = Number(raw)
  return Number.isFinite(parsed) ? parsed : null
}

export async function saveLocalWalletSetupSucceededAtMs(timestampMs: number): Promise<void> {
  await writeRecord(SETUP_SUCCEEDED_AT_RECORD, String(timestampMs))
}

export async function loadLocalWalletBackupSavedAck(): Promise<boolean> {
  const raw = await readRecord(BACKUP_SAVED_ACK_RECORD)
  return raw === "1"
}

export async function saveLocalWalletBackupSavedAck(): Promise<void> {
  await writeRecord(BACKUP_SAVED_ACK_RECORD, "1")
}
