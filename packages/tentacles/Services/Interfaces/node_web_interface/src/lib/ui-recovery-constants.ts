export const SESSION_HEARTBEAT_KEY = "octobot_ui_session_heartbeat"
export const SESSION_ID_KEY = "octobot_ui_session_id"
export const BOOT_FAILED_FLAG = "__octobotBootFailed"
export const BOOT_SUCCEEDED_FLAG = "__octobotBootSucceeded"

export const SESSION_HEARTBEAT_STALE_MS = 30_000
export const BOOT_TIMEOUT_MS = 5_000
export const DEVICE_DATABASE_NAME = "octobot_device"

export const RESET_CONFIRM_MESSAGE =
  "This will clear all local browser data for OctoBot Node on this device " +
  "(login, templates, encryption keys). You will need to set up again. Continue?"

export const RECOVERY_EXPLANATION =
  "Local browser data for this app may be corrupt or inconsistent. " +
  "Resetting clears all site data for OctoBot Node on this device."
