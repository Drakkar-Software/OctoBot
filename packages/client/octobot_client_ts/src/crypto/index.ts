export { createSecretEncryptor, createRawKeyEncryptor } from './secretEncryptor.js'
export { deriveCollectionKeys, decodeCollectionKey } from './collectionKeys.js'
export { deriveAesKeyBytes } from './hkdf.js'
export {
  SYNC_MOUNT_PATH,
  SYNC_NAMESPACE,
  SYNC_FETCH_TIMEOUT_MS,
  DEFAULT_PROBE_TIMEOUT_MS,
  STARFISH_ENCRYPTION_SALT,
} from './wireConstants.js'
