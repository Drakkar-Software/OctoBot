/**
 * Wallet-bound OctoChat identity.
 *
 * The OctoChat support identity is derived deterministically from the OctoBot wallet via
 * `deriveRootIdentityFromEvmSignature`: the node signs a fixed challenge with the wallet
 * (`GET /api/v1/config/octochat-identity`) and the browser pipes that signature through the SDK.
 * Same OctoBot account → same OctoChat identity (and the same support ticket) on every device —
 * unlike a random per-browser device key.
 *
 * The derived identity is cached encrypted-at-rest (via `device-key`) and keyed by wallet address
 * so switching wallets re-derives. The wallet signature itself is private-key-equivalent for the
 * derived identity and is consumed once — never persisted.
 */
import { clearSpaceAccessStore } from "@drakkar.software/octochat-sdk"
import { kvRemove } from "@drakkar.software/octochat-sdk/platform"
import { deriveRootIdentityFromEvmSignature } from "@drakkar.software/starfish-identities"

import { loadOctoChatKeys, saveOctoChatKeys } from "@/lib/device-key"

// MUST stay byte-identical to the node challenge in
// packages/tentacles/Services/Interfaces/node_api_interface/api/routes/config.py.
export const OCTOCHAT_IDENTITY_CHALLENGE = "octochat:support-identity"

export interface OctoChatKeyPair {
  edPriv: string
  edPub: string
  kemPriv: string
  kemPub: string
}

export interface OctoChatIdentity {
  userId: string
  keys: OctoChatKeyPair
}

interface StoredIdentity extends OctoChatIdentity {
  /** Lowercased wallet address this identity was derived from. */
  address: string
}

/** Decode a hex string (with or without `0x`) into bytes. */
export function hexToBytes(hex: string): Uint8Array {
  const clean = hex.startsWith("0x") ? hex.slice(2) : hex
  const bytes = new Uint8Array(clean.length / 2)
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = Number.parseInt(clean.slice(i * 2, i * 2 + 2), 16)
  }
  return bytes
}

/**
 * Resolve the wallet-bound OctoChat identity, deriving (and caching) it on first use for the
 * current wallet. `buildAuthHeader` authenticates the call that fetches the wallet signature.
 */
export async function getWalletBoundIdentity(
  buildAuthHeader: () => Promise<string>,
): Promise<OctoChatIdentity> {
  const address = (localStorage.getItem("auth_username") || "").toLowerCase()

  const stored = await loadOctoChatKeys()
  if (stored) {
    const parsed = JSON.parse(stored) as Partial<StoredIdentity>
    if (parsed.keys && parsed.userId && parsed.address === address) {
      return { userId: parsed.userId, keys: parsed.keys }
    }
    if (parsed.userId) {
      clearSpaceAccessStore()
      await kvRemove(`dk.spaceaccess.${parsed.userId}`).catch(() => undefined)
    }
  }

  const res = await fetch("/api/v1/config/octochat-identity", {
    headers: { Authorization: await buildAuthHeader() },
  })
  if (!res.ok) {
    throw new Error(`Failed to load OctoChat identity (${res.status})`)
  }
  const { address: signerAddress, signature } = (await res.json()) as {
    address: string
    signature: string
  }

  const identity = await deriveRootIdentityFromEvmSignature({
    address: signerAddress,
    signature: hexToBytes(signature),
    challenge: OCTOCHAT_IDENTITY_CHALLENGE,
  })

  const record: StoredIdentity = {
    address: signerAddress.toLowerCase(),
    userId: identity.userId,
    keys: identity.keys,
  }
  await saveOctoChatKeys(JSON.stringify(record))
  return { userId: identity.userId, keys: identity.keys }
}
