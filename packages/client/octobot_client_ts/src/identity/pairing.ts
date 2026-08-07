import { generateDeviceKeys, mintDeviceCap, type GeneratedDeviceKeys, type ScopePreset } from '@drakkar.software/starfish-identities'
import type { CapCert } from '@drakkar.software/starfish-protocol'
import { deriveRoot, type KeyDerivation } from './capProvider.js'
import { createKeyCache } from './keys.js'
import type { NodeEndpoint } from '../transport/urls.js'
import { deriveCollectionKeys } from '../crypto/collectionKeys.js'
import { NODE_COLLECTIONS, type NodeCollectionKey } from '../collections/nodeCollections.js'

/** The two node collections a read-only pairing grants by default: enough to
 *  reconstruct `accounts.list()`, `automations.list()`, AND `strategies.list()`
 *  (the latter is implemented via a `userData` pull, not the legacy
 *  `strategies` collection) — with no access to `settings`, `accountTrading`,
 *  or the `strategies` collection itself. */
const DEFAULT_READ_ONLY_COLLECTIONS: readonly NodeCollectionKey[] = ['userData', 'accounts']

function assertKnownCollections(collections: readonly string[]): asserts collections is NodeCollectionKey[] {
  const unknown = collections.filter((c) => !(c in NODE_COLLECTIONS))
  if (unknown.length) {
    throw new Error(`createReadOnlyPairing: unknown collection(s): ${unknown.join(', ')}`)
  }
}

/** A read-only device's bearer credential: an ephemeral keypair this device
 *  generated itself, plus a cap-cert the wallet's root key signed for it,
 *  plus one derived AES-256 key per granted collection (`collectionKeys`) —
 *  each `HKDF-SHA256(secret, salt, collection.encryptionInfo)`, the same
 *  derivation `createSecretEncryptor` performs internally, stopped one step
 *  early so the raw bytes can travel here. That derivation is one-way and
 *  collection-independent: holding `collectionKeys.userData` reveals nothing
 *  about `collectionKeys.accounts`, and neither reveals the wallet's
 *  derived secret, let alone the wallet's private key. A device holding
 *  this payload can decrypt exactly the granted collections and nothing
 *  else, and can never widen its own grant (it never touches the root
 *  private key). See `crypto/collectionKeys.ts`. */
export interface ReadOnlyPairingPayload {
  v: 2
  kind: 'octobot-read-only-pairing'
  node: NodeEndpoint
  rootEdPub: string
  userId: string
  device: GeneratedDeviceKeys
  cap: CapCert
  scope: ScopePreset
  collectionKeys: Partial<Record<NodeCollectionKey, string>>
}

/** Mint a read-only pairing payload from the wallet's seed. The caller (e.g.
 *  mobile2) renders the returned string as a QR code for another device to
 *  scan — this package never renders QR images itself. The payload is fully
 *  self-contained (it carries the node's endpoint), so
 *  `connectReadOnlyDevice()` needs nothing else to connect. */
export async function createReadOnlyPairing(
  seed: string,
  derivation: KeyDerivation,
  node: NodeEndpoint,
  opts?: { collections?: string[]; ttlSec?: number },
): Promise<{ payload: string }> {
  const root = await deriveRoot(seed, derivation)
  const device = generateDeviceKeys()
  const collections = opts?.collections ?? DEFAULT_READ_ONLY_COLLECTIONS
  assertKnownCollections(collections)
  const scope: ScopePreset = {
    ops: ['read', 'list'],
    collections,
  }
  const cap = await mintDeviceCap(
    root.keys.edPriv,
    root.keys.edPub,
    { edPubHex: device.edPub, kemPubHex: device.kemPub },
    scope,
    opts?.ttlSec != null ? { ttlSec: opts.ttlSec } : undefined,
  )
  const secret = await createKeyCache().getEncryptionKey(seed, derivation)
  const collectionKeys = deriveCollectionKeys(secret, collections)
  const payload: ReadOnlyPairingPayload = {
    v: 2,
    kind: 'octobot-read-only-pairing',
    node,
    rootEdPub: root.keys.edPub,
    userId: root.userId,
    device,
    cap,
    scope,
    collectionKeys,
  }
  return { payload: JSON.stringify(payload) }
}

/** Parse and structurally validate a scanned/pasted read-only pairing
 *  payload. Throws on anything that isn't shaped like one — callers doing QR
 *  classification (e.g. `classifyScannedCode`) should catch and fall through
 *  to the next candidate parser rather than propagate. */
export function parseReadOnlyPairing(payload: string): ReadOnlyPairingPayload {
  let parsed: unknown
  try {
    parsed = JSON.parse(payload)
  } catch {
    throw new Error('not valid JSON')
  }
  if (typeof parsed !== 'object' || parsed === null) throw new Error('not an object')
  const p = parsed as Record<string, unknown>
  // A v1 payload (this package's earlier, retired pairing format) is a
  // RECOGNIZED-but-stale payload, not an unrecognized one — a user holding
  // an old QR should be told to re-pair, not that the code is unreadable.
  if (p.v === 1 && p.kind === 'octobot-read-only-pairing') {
    throw new Error('read-only pairing payload is out of date (v1) — re-pair this device to get a current one')
  }
  if (p.v !== 2 || p.kind !== 'octobot-read-only-pairing') throw new Error('not a read-only pairing payload')
  if (typeof p.rootEdPub !== 'string' || typeof p.userId !== 'string') {
    throw new Error('malformed read-only pairing payload')
  }
  const node = p.node as NodeEndpoint | undefined
  if (!node || typeof node.host !== 'string' || typeof node.port !== 'number') {
    throw new Error('malformed read-only pairing payload: node')
  }
  const device = p.device as GeneratedDeviceKeys | undefined
  if (!device || typeof device.edPriv !== 'string' || typeof device.kemPriv !== 'string') {
    throw new Error('malformed read-only pairing payload: device')
  }
  const cap = p.cap as CapCert | undefined
  if (!cap || cap.v !== 1 || typeof cap.sig !== 'string') {
    throw new Error('malformed read-only pairing payload: cap')
  }
  if (typeof p.collectionKeys !== 'object' || p.collectionKeys === null) {
    throw new Error('malformed read-only pairing payload: collectionKeys')
  }
  return p as unknown as ReadOnlyPairingPayload
}
