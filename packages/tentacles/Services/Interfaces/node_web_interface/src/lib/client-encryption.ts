export const CLIENT_KEY_NAMES = ["rsa_public", "ecdsa_private", "rsa_private", "ecdsa_public"] as const
export type ClientKeyName = (typeof CLIENT_KEY_NAMES)[number]

export const CLIENT_KEY_LABELS: Record<ClientKeyName, string> = {
  rsa_public: "TASKS_OUTPUTS_RSA_PUBLIC_KEY",
  ecdsa_private: "TASKS_OUTPUTS_ECDSA_PRIVATE_KEY",
  rsa_private: "TASKS_OUTPUTS_RSA_PRIVATE_KEY",
  ecdsa_public: "TASKS_OUTPUTS_ECDSA_PUBLIC_KEY",
}

export type ClientKeys = Record<ClientKeyName, string>

export function emptyKeys(): ClientKeys {
  return { rsa_public: "", ecdsa_private: "", rsa_private: "", ecdsa_public: "" }
}

export function areClientKeysConfigured(keys: ClientKeys): boolean {
  return CLIENT_KEY_NAMES.every((k) => keys[k].trim())
}
