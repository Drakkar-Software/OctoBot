const DB_NAME = "octobot_device"
const STORE_NAME = "secure_storage"
const DEVICE_KEY_RECORD = "device_key"
const AUTH_PASSWORD_RECORD = "auth_password"
const CLIENT_KEYS_RECORD = "client_keys"

interface EncryptedRecord {
  iv: Uint8Array
  ciphertext: ArrayBuffer
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1)
    req.onupgradeneeded = () => {
      req.result.createObjectStore(STORE_NAME)
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

function idbGet<T>(store: IDBObjectStore, key: string): Promise<T | undefined> {
  return new Promise((resolve, reject) => {
    const req = store.get(key)
    req.onsuccess = () => resolve(req.result as T | undefined)
    req.onerror = () => reject(req.error)
  })
}

function idbPut(store: IDBObjectStore, key: string, value: unknown): Promise<void> {
  return new Promise((resolve, reject) => {
    const req = store.put(value, key)
    req.onsuccess = () => resolve()
    req.onerror = () => reject(req.error)
  })
}

function idbDelete(store: IDBObjectStore, key: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const req = store.delete(key)
    req.onsuccess = () => resolve()
    req.onerror = () => reject(req.error)
  })
}

async function getOrCreateDeviceKey(): Promise<CryptoKey> {
  const readDb = await openDB()
  const existing = await idbGet<CryptoKey>(
    readDb.transaction(STORE_NAME, "readonly").objectStore(STORE_NAME),
    DEVICE_KEY_RECORD,
  )
  if (existing) return existing

  const key = await crypto.subtle.generateKey(
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  )
  const writeDb = await openDB()
  await idbPut(
    writeDb.transaction(STORE_NAME, "readwrite").objectStore(STORE_NAME),
    DEVICE_KEY_RECORD,
    key,
  )
  return key
}

async function encryptWithDeviceKey(plaintext: string): Promise<EncryptedRecord> {
  const key = await getOrCreateDeviceKey()
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    key,
    new TextEncoder().encode(plaintext),
  )
  return { iv, ciphertext }
}

async function decryptWithDeviceKey(record: EncryptedRecord): Promise<string> {
  const key = await getOrCreateDeviceKey()
  const plaintext = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: record.iv as unknown as ArrayBuffer },
    key,
    record.ciphertext,
  )
  return new TextDecoder().decode(plaintext)
}

async function idbSaveRecord(recordKey: string, plaintext: string): Promise<void> {
  const record = await encryptWithDeviceKey(plaintext)
  const db = await openDB()
  await idbPut(
    db.transaction(STORE_NAME, "readwrite").objectStore(STORE_NAME),
    recordKey,
    record,
  )
}

async function idbLoadRecord(recordKey: string): Promise<string | null> {
  try {
    const db = await openDB()
    const record = await idbGet<EncryptedRecord>(
      db.transaction(STORE_NAME, "readonly").objectStore(STORE_NAME),
      recordKey,
    )
    if (!record) return null
    return await decryptWithDeviceKey(record)
  } catch {
    return null
  }
}

async function idbClearRecord(recordKey: string): Promise<void> {
  const db = await openDB()
  await idbDelete(
    db.transaction(STORE_NAME, "readwrite").objectStore(STORE_NAME),
    recordKey,
  )
}

export async function savePassword(password: string): Promise<void> {
  await idbSaveRecord(AUTH_PASSWORD_RECORD, password)
}

export async function loadPassword(): Promise<string | null> {
  return idbLoadRecord(AUTH_PASSWORD_RECORD)
}

export async function clearPassword(): Promise<void> {
  await idbClearRecord(AUTH_PASSWORD_RECORD)
}

export async function saveClientKeys(keys: Record<string, string>): Promise<void> {
  await idbSaveRecord(CLIENT_KEYS_RECORD, JSON.stringify(keys))
}

export async function loadClientKeys(): Promise<Record<string, string> | null> {
  const raw = await idbLoadRecord(CLIENT_KEYS_RECORD)
  if (!raw) return null
  return JSON.parse(raw) as Record<string, string>
}

export async function clearClientKeys(): Promise<void> {
  await idbClearRecord(CLIENT_KEYS_RECORD)
}

export async function hasStoredClientKeys(): Promise<boolean> {
  const db = await openDB()
  const record = await idbGet(
    db.transaction(STORE_NAME, "readonly").objectStore(STORE_NAME),
    CLIENT_KEYS_RECORD,
  )
  return record !== undefined
}
