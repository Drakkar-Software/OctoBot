const DB_NAME = "octobot_device"
const STORE_NAME = "secure_storage"
const DEVICE_KEY_RECORD = "device_key"
const AUTH_PASSWORD_RECORD = "auth_password"
const CLIENT_KEYS_PREFIX = "client_keys:"
const OCTOCHAT_KEYS_RECORD = "octochat_device_keys"

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

function idbPut(
  store: IDBObjectStore,
  key: string,
  value: unknown,
): Promise<void> {
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

async function encryptWithKey(
  key: CryptoKey,
  plaintext: string,
): Promise<EncryptedRecord> {
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    key,
    new TextEncoder().encode(plaintext),
  )
  return { iv, ciphertext }
}

async function decryptWithKey(
  key: CryptoKey,
  record: EncryptedRecord,
): Promise<string> {
  const plaintext = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: record.iv as unknown as ArrayBuffer },
    key,
    record.ciphertext,
  )
  return new TextDecoder().decode(plaintext)
}

async function encryptWithDeviceKey(
  plaintext: string,
): Promise<EncryptedRecord> {
  return encryptWithKey(await getOrCreateDeviceKey(), plaintext)
}

async function decryptWithDeviceKey(record: EncryptedRecord): Promise<string> {
  return decryptWithKey(await getOrCreateDeviceKey(), record)
}

async function idbSaveRecord(
  recordKey: string,
  plaintext: string,
): Promise<void> {
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

// OctoChat support-desk identity, cached encrypted-at-rest. The stored value is the
// wallet-bound identity ({ address, userId, keys }) derived deterministically from the OctoBot
// wallet (see lib/octochat-identity.ts), keyed by address so switching wallets re-derives.
export async function saveOctoChatKeys(value: string): Promise<void> {
  await idbSaveRecord(OCTOCHAT_KEYS_RECORD, value)
}

export async function loadOctoChatKeys(): Promise<string | null> {
  return idbLoadRecord(OCTOCHAT_KEYS_RECORD)
}

// Derive a deterministic AES-GCM key from a wallet passphrase and address via PBKDF2.
// Each wallet gets a unique key — keys stored by one wallet cannot be decrypted by another.
export async function derivePassphraseKey(
  passphrase: string,
  address: string,
): Promise<CryptoKey> {
  const baseKey = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(passphrase),
    "PBKDF2",
    false,
    ["deriveKey"],
  )
  return crypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      salt: new TextEncoder().encode(address.toLowerCase()),
      iterations: 100_000,
      hash: "SHA-256",
    },
    baseKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  )
}

function clientKeysRecord(address: string): string {
  return `${CLIENT_KEYS_PREFIX}${address.toLowerCase()}`
}

export async function saveClientKeys(
  keys: Record<string, string>,
): Promise<void> {
  const address = localStorage.getItem("auth_username")
  const passphrase = await loadPassword()
  if (!address || !passphrase)
    throw new Error("No active wallet session — cannot save client keys")
  const key = await derivePassphraseKey(passphrase, address)
  const record = await encryptWithKey(key, JSON.stringify(keys))
  const db = await openDB()
  await idbPut(
    db.transaction(STORE_NAME, "readwrite").objectStore(STORE_NAME),
    clientKeysRecord(address),
    record,
  )
}

export async function loadClientKeys(): Promise<Record<string, string> | null> {
  const address = localStorage.getItem("auth_username")
  const passphrase = await loadPassword()
  if (!address || !passphrase) return null

  const recordKey = clientKeysRecord(address)
  const db = await openDB()

  const record = await idbGet<EncryptedRecord>(
    db.transaction(STORE_NAME, "readonly").objectStore(STORE_NAME),
    recordKey,
  )

  if (!record) return null

  try {
    const key = await derivePassphraseKey(passphrase, address)
    const raw = await decryptWithKey(key, record)
    return JSON.parse(raw) as Record<string, string>
  } catch {
    return null
  }
}

export async function clearClientKeys(): Promise<void> {
  const address = localStorage.getItem("auth_username")
  if (!address) return
  await idbClearRecord(clientKeysRecord(address))
}

export async function hasStoredClientKeys(): Promise<boolean> {
  const keys = await loadClientKeys()
  return keys !== null && Object.values(keys).every((v) => v.trim().length > 0)
}
