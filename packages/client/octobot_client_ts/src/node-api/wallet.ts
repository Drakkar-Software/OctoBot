// Turning what a node hands over into a wallet an app can hold.
//
// A node's mnemonic is real BIP44 (`web3.Account.create_with_mnemonic`),
// which is also this package's only derivation scheme today — so importing
// one is unambiguous. This file exists for the two cases that still need
// their own handling: a raw key (no derivation at all — `derivation:
// 'legacy'` here just means "the key IS the identity," not any specific
// scheme) and an older node's HTTP export, which hands over both the phrase
// and the key it must actually agree with.
import { classifyBareSecret, classifySecret, readSecretEnvelope } from '../identity/secret.js'
import { deriveBip44PrivateKey, isEvmPrivateKey, normalizeEvmPrivateKey } from '../identity/evm.js'
import { parseNodePairingQr, type NodePairingPayload } from './pairing.js'
import type { NodeWalletExport } from './setup.js'
import { parseReadOnlyPairing, type ReadOnlyPairingPayload } from '../identity/pairing.js'
import { decodeActionProposal, type ActionProposal } from '../protocol/proposal.js'

/** A wallet resolved from a node, ready to be stored.
 *
 *  `seed` is what the user backs up; `key` is what the app signs and encrypts
 *  with. They differ whenever the phrase needs a derivation the app does not use
 *  natively, which `derivation` records. */
export type NodeWalletImport = {
  seed: string
  keySource: 'mnemonic' | 'privateKey'
  derivation: 'legacy' | 'bip44'
  key?: string
}

/** From a pairing QR's secret, which is the wallet itself — a BIP39 phrase, or a
 *  0x private key when the node was set up from a raw key and has no mnemonic.
 *  Null when it is neither, which has to fail the scan rather than quietly
 *  produce a wallet nobody owns. */
export async function nodeWalletFromSecret(secret: string): Promise<NodeWalletImport | null> {
  const classified = await classifySecret(secret)

  if (classified.kind === 'privateKey') {
    // No derivation to get wrong: the key is the identity.
    return { seed: classified.value, keySource: 'privateKey', derivation: 'legacy' }
  }
  if (classified.kind === 'seed') {
    return {
      seed: classified.value,
      keySource: 'mnemonic',
      derivation: 'bip44',
      key: await deriveBip44PrivateKey(classified.value),
    }
  }
  return null
}

/** From an older node's HTTP wallet export, which hands over both halves. The
 *  node's own `private_key` is authoritative for the identity — nothing has to be
 *  derived to get that right — but its mnemonic is worth keeping as the thing the
 *  user backs up. Null when the export carries no usable key, which is a node
 *  with nothing to import rather than a code that failed to decode. */
export async function nodeWalletFromExport(
  wallet: NodeWalletExport,
): Promise<NodeWalletImport | null> {
  const key = normalizeEvmPrivateKey(wallet.private_key)
  if (!isEvmPrivateKey(key)) return null

  // The phrase is only kept if it really does derive to the key the node signs
  // with. Both come from one wallet object on the node, so they should always
  // agree — but a phrase offered as a backup that restores a *different* account
  // in another wallet is worse than offering no phrase at all, and this is the
  // only place that can check rather than assume.
  if (wallet.seed) {
    const fromSeed = await nodeWalletFromSecret(wallet.seed)
    if (fromSeed?.key === key) return fromSeed
  }
  return { seed: key, keySource: 'privateKey', derivation: 'legacy' }
}

/** The key material a resolved wallet is identified by. */
export function nodeWalletKey(wallet: NodeWalletImport): string {
  return wallet.key ?? wallet.seed
}

/** What a code held up to a wallet scanner turned out to be. */
export type ScannedCode =
  | { kind: 'node'; payload: NodePairingPayload }
  | { kind: 'octobotReadOnlyPairing'; payload: ReadOnlyPairingPayload }
  | { kind: 'octobotActionProposal'; payload: ActionProposal }
  | { kind: 'privateKey'; value: string }
  | { kind: 'seed'; value: string }
  | { kind: 'unknown' }

/** Classify a scanned code. Node pairing JSON and the two octobot-client JSON
 *  shapes (read-only pairing, action proposal) are checked first because
 *  they're the most specific — each has its own `v`/`kind` discriminator and
 *  throws immediately on anything else. A standalone envelope next, since its
 *  field name says the value is key material; a bare code last, where the
 *  shape is all there is to go on. */
export async function classifyScannedCode(data: string): Promise<ScannedCode> {
  const payload = parseNodePairingQr(data)
  if (payload) return { kind: 'node', payload }

  try {
    return { kind: 'octobotReadOnlyPairing', payload: parseReadOnlyPairing(data) }
  } catch {
    // not a read-only pairing payload — fall through
  }

  try {
    return { kind: 'octobotActionProposal', payload: decodeActionProposal(data) }
  } catch {
    // not an action proposal payload — fall through
  }

  const enveloped = readSecretEnvelope(data)
  if (enveloped !== null) return classifySecret(enveloped)

  return classifyBareSecret(data)
}
