import type { StarfishCapProvider, StarfishClient } from '@drakkar.software/starfish-client'
import type { Encryptor } from '@drakkar.software/starfish-protocol'
import { WalletCapProvider, type KeyDerivation } from '../../identity/capProvider.js'
import { createKeyCache } from '../../identity/keys.js'
import { createSyncClient } from '../../transport/syncClient.js'
import type { NodeEndpoint } from '../../transport/urls.js'
import type { NodeCredentials } from '../../transport/rest.js'
import { SYNC_FETCH_TIMEOUT_MS } from '../../crypto/wireConstants.js'
import { STARFISH_ENCRYPTION_SALT } from '../../crypto/wireConstants.js'
import { createSecretEncryptor, createRawKeyEncryptor } from '../../crypto/secretEncryptor.js'
import { decodeCollectionKey } from '../../crypto/collectionKeys.js'
import { NODE_COLLECTIONS, type NodeCollectionKey } from '../../collections/nodeCollections.js'
import { OctoBotScopeError } from './errors.js'

/** What `ClientSession.capProvider` needs beyond the bare `StarfishCapProvider`
 *  the sync client itself requires — `connect.ts`'s `finalize()` also reads
 *  `getUserId()` off it. `WalletCapProvider` satisfies this; so does the
 *  installed-credential adapter `connectReadOnlyDevice()` builds — a
 *  read-only session never derives a root key at all, so it can't be a real
 *  `WalletCapProvider`. */
export interface SessionCapProvider extends StarfishCapProvider {
  getUserId(): Promise<string>
}

/** Everything a `client/*.ts` API module (`accounts.ts`, `automations.ts`,
 *  `strategies.ts`, `settings.ts`, `actionHandle.ts`, `documents.ts`) closes
 *  over. Both a full-wallet session (`createSession`) and a read-only
 *  pairing session (`createReadOnlySession`) satisfy this — the two differ
 *  only in what `collectionEncryptor` can do, which is exactly the point:
 *  it is the single place collection-scope enforcement lives.
 *
 *  `seed`/`derivation`/`address` are deliberately NOT here — they belong to
 *  `WalletClientSession` below, read only by `connect.ts`. If a shared API
 *  module ever needs one of those fields, that is a sign it leaked a
 *  wallet-only assumption into code the read-only path also runs. */
export type ClientSession = {
  readonly origin: string
  readonly node: NodeEndpoint
  readonly userId: string
  readonly fetch: typeof fetch
  readonly defaultTimeoutMs: number
  readonly basicAuth?: NodeCredentials
  readonly capProvider: SessionCapProvider
  readonly syncClient: StarfishClient
  /** Resolve the `Encryptor` for one node collection. A full-wallet session
   *  can derive this for any collection on demand; a read-only session can
   *  only do so for the collections its pairing grant actually covers, and
   *  throws `OctoBotScopeError` for anything else. See `OctoBotScopeError`'s
   *  doc comment for why this client-side check currently matters more than
   *  it should. */
  collectionEncryptor(collection: NodeCollectionKey): Promise<Encryptor>
  /** Drops whatever derived-key state this session holds. Does not touch
   *  in-flight requests. */
  close(): void
}

/** The full-wallet session `connect.ts` builds, on top of `ClientSession`.
 *  `address`/`derivation`/`seed`/`walletAddress()` are read only inside
 *  `connect.ts` itself (to re-derive the wallet address after the cap
 *  provider resolves `userId`, and to surface `OctoBotClient.address`) —
 *  nothing in the shared `client/*.ts` API modules touches them. */
export type WalletClientSession = ClientSession & {
  readonly address: string
  readonly derivation: KeyDerivation
  readonly seed: string
  /** The EVM address `seed` derives to under `derivation`. Backed by the
   *  same derived-key cache `collectionEncryptor` uses internally — kept off
   *  the shared `ClientSession` surface so a read-only session (which has no
   *  such cache) never needs to fake it. */
  walletAddress(): Promise<string>
}

export function createSession(opts: {
  origin: string
  node: NodeEndpoint
  address: string
  userId: string
  derivation: KeyDerivation
  seed: string
  fetch: typeof fetch
  defaultTimeoutMs: number
  basicAuth?: NodeCredentials
}): WalletClientSession {
  const capProvider = new WalletCapProvider(opts.seed, opts.derivation)
  const keyCache = createKeyCache()
  const syncClient = createSyncClient({
    origin: opts.origin,
    capProvider,
    fetch: opts.fetch,
    timeoutMs: opts.defaultTimeoutMs || SYNC_FETCH_TIMEOUT_MS,
  })

  return {
    origin: opts.origin,
    node: opts.node,
    address: opts.address,
    userId: opts.userId,
    derivation: opts.derivation,
    seed: opts.seed,
    fetch: opts.fetch,
    defaultTimeoutMs: opts.defaultTimeoutMs,
    basicAuth: opts.basicAuth,
    capProvider,
    syncClient,
    async collectionEncryptor(collection) {
      const secret = await keyCache.getEncryptionKey(opts.seed, opts.derivation)
      return createSecretEncryptor(secret, STARFISH_ENCRYPTION_SALT, NODE_COLLECTIONS[collection].encryptionInfo)
    },
    walletAddress: () => keyCache.getWalletAddress(opts.seed, opts.derivation),
    close: () => keyCache.clear(),
  }
}

/** Builds a `ClientSession` for an installed read-only pairing credential —
 *  no seed, no root key, no `WalletCapProvider`. `capProvider` is a thin
 *  inline adapter over the already-signed cap-cert the pairing payload
 *  carries. `collectionKeys` is the payload's per-collection subkey map
 *  (see `identity/pairing.ts`'s `ReadOnlyPairingPayload.collectionKeys` and
 *  `crypto/collectionKeys.ts`) — each key decrypts exactly one collection,
 *  derived one-way from the wallet secret, so this session can never
 *  reconstruct that secret or decrypt a collection outside the grant. */
export function createReadOnlySession(opts: {
  origin: string
  node: NodeEndpoint
  userId: string
  fetch: typeof fetch
  defaultTimeoutMs: number
  capProvider: SessionCapProvider
  collectionKeys: Partial<Record<NodeCollectionKey, string>>
}): ClientSession {
  const syncClient = createSyncClient({
    origin: opts.origin,
    capProvider: opts.capProvider,
    fetch: opts.fetch,
    timeoutMs: opts.defaultTimeoutMs || SYNC_FETCH_TIMEOUT_MS,
  })

  return {
    origin: opts.origin,
    node: opts.node,
    userId: opts.userId,
    fetch: opts.fetch,
    defaultTimeoutMs: opts.defaultTimeoutMs,
    capProvider: opts.capProvider,
    syncClient,
    async collectionEncryptor(collection) {
      const key = opts.collectionKeys[collection]
      if (key === undefined) throw new OctoBotScopeError(collection)
      return createRawKeyEncryptor(decodeCollectionKey(key))
    },
    // No derived-key cache on this path — nothing to drop.
    close: () => {},
  }
}
