import { normalizeEvmPrivateKey } from "@drakkar.software/octobot-client/identity"
import { bytesToHex } from "./hex"

/** A fresh, local-only secp256k1 private key for demo panels — never derived
 *  from a mnemonic, never sent anywhere. Every panel that needs a throwaway
 *  wallet generates one of these instead of a BIP39 phrase. */
export function generateRandomPrivateKey(): string {
  const bytes = new Uint8Array(32)
  crypto.getRandomValues(bytes)
  return normalizeEvmPrivateKey(bytesToHex(bytes))
}
