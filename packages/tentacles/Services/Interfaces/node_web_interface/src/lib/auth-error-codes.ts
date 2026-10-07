/** Machine identifiers returned by the node API (`detail.code`). UI copy lives in auth-error-messages.ts. */

export const API_AUTH_ERROR_CODES = {
  AUTH_PASSPHRASE_REQUIRED: "auth_passphrase_required",
  AUTH_WALLET_ADDRESS_REQUIRED: "auth_wallet_address_required",
  AUTH_WALLET_NOT_FOUND: "auth_wallet_not_found",
  AUTH_INVALID_PASSPHRASE: "auth_invalid_passphrase",
  AUTH_NODE_NOT_CONFIGURED: "auth_node_not_configured",
} as const

export type ApiAuthErrorCode =
  (typeof API_AUTH_ERROR_CODES)[keyof typeof API_AUTH_ERROR_CODES]

export const CLIENT_AUTH_ERROR_CODES = {
  AUTH_SESSION_INCOMPLETE: "client_auth_session_incomplete",
  DEVICE_STORAGE_BLOCKED: "client_device_storage_blocked",
  NETWORK_ERROR: "client_network_error",
  SESSION_CLEARED: "client_session_cleared",
} as const

export type ClientAuthErrorCode =
  (typeof CLIENT_AUTH_ERROR_CODES)[keyof typeof CLIENT_AUTH_ERROR_CODES]

export type AuthErrorCode = ApiAuthErrorCode | ClientAuthErrorCode
