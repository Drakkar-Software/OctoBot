// Literal strings and numbers shared with the node's Python implementation.
// A change on either side breaks sync SILENTLY — see tests/wireContract.test.ts
// and https://docs.octobot.cloud/client-sdk/wire-contract for the full inventory.

/** The server mounts the sync sub-app at this path. The Starfish client
 *  receives this as the baseUrl suffix and handles /v1/{namespace}/... internally. */
export const SYNC_MOUNT_PATH = 'sync'
export const SYNC_NAMESPACE = 'octobot'

/** Per-request timeout on sync clients. Bounds a merging pull's write-gating
 *  window when the target node is offline (raw fetch would hang for the OS
 *  TCP timeout, 60s+). Documents are small JSON — 10s is ample for push too. */
export const SYNC_FETCH_TIMEOUT_MS = 10_000
export const DEFAULT_PROBE_TIMEOUT_MS = 4000

/** HKDF salt for identity-encryption key derivation.
 *  @see packages/sync/octobot_sync/constants.py — HKDF_SALT_STRING
 *  @remarks Changing this breaks decryption of every existing document. */
export const STARFISH_ENCRYPTION_SALT = 'octobot-starfish-identity-v1'
