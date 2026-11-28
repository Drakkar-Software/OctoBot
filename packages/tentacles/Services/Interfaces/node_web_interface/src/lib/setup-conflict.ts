export const NODE_ALREADY_INITIALIZED_MESSAGE =
  "This Node has already been initialized. It can only be set up once."

export const LOGIN_NODE_ALREADY_INITIALIZED_STORAGE_KEY =
  "octobot_login_node_already_initialized"

export function markNodeAlreadyInitialized(): void {
  sessionStorage.setItem(LOGIN_NODE_ALREADY_INITIALIZED_STORAGE_KEY, "1")
}

export function isSetupAlreadyConfiguredConflict(
  httpStatus: number | undefined,
): boolean {
  return httpStatus === 409
}

export function consumeNodeAlreadyInitializedHint(): boolean {
  const value = sessionStorage.getItem(LOGIN_NODE_ALREADY_INITIALIZED_STORAGE_KEY)
  if (!value) {
    return false
  }
  sessionStorage.removeItem(LOGIN_NODE_ALREADY_INITIALIZED_STORAGE_KEY)
  return true
}