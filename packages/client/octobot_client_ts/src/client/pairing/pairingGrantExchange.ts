import { seal, unseal, type SealerKeys, type SealedBlob } from '@drakkar.software/starfish-keyring'
import { ConflictError } from '@drakkar.software/starfish-client'
import type { CapCert } from '@drakkar.software/starfish-protocol'
import type { GeneratedDeviceKeys } from '@drakkar.software/starfish-identities'
import type { PairingRequestPayload } from '../../identity/pairingRequest.js'
import {
  createRendezvousClient,
  pullRendezvousDoc,
  pushRendezvousDoc,
  clearRendezvousDoc,
  joinSessionPath,
} from '../../transport/rendezvous.js'
import { pollDelay } from '../../protocol/poll.js'
import { abortableSleep } from './pairingRequest.js'
import { OctoBotConnectionError, OctoBotConflictError, rethrowAsOctoBotError } from '../core/errors.js'
import {
  readMirrorCollections,
  parseMirrorGrantBundle,
  type MirrorGrantNodeRef,
} from './mirrorReader.js'
import type { MintedPairingGrant } from './mirrorGrant.js'
import type { MirrorCollectionId } from '../mirror/index.js'

/**
 * Website↔phone exchange for the read-only-device grant this package mints
 * against the space-mirror (see `mirrorGrant.ts`). This replaced an older
 * sealed data-snapshot exchange, which has since been deleted.
 *
 * Request and grant now share ONE rendezvous address, `joinSessionPath(code)`
 * (the `joinsessions` collection — see `transport/rendezvous.ts`), not two
 * separate collections. `startPairingRequest`/`fetchPairingRequestByCode`
 * publish/read the "request" phase there; this file's `publishPairingGrant`
 * OVERWRITES that same doc with the "grant" phase once the phone approves.
 * The sealing mechanism itself is unchanged (`starfish-keyring`'s
 * `seal`/`unseal`, sealed to the website's ephemeral KEM key, signed by the
 * wallet's own root key) — what's new is the OUTER wire envelope
 * (`v`/`kind`/`sealed`, see `JoinSessionGrantDoc` below) wrapping the sealed
 * blob, so a poller can tell "still just a request" from "a grant has been
 * published" by reading one unsealed field, without attempting `unseal()`
 * on a doc that might not even be sealed yet.
 */

const GRANT_ENVELOPE_KIND = 'octobot-pairing-grant'
const GRANT_ENVELOPE_VERSION = 1

/** The sealed plaintext's own shape — unchanged by the joinsessions merge.
 *  `unseal()` decrypts a `JoinSessionGrantDoc.sealed` blob down to exactly
 *  this JSON. */
interface GrantEnvelope {
  v: typeof GRANT_ENVELOPE_VERSION
  kind: typeof GRANT_ENVELOPE_KIND
  bundle: string
}

/** The UNSEALED document actually written to `joinSessionPath(code)` for the
 *  grant phase. `v`/`kind` here are plaintext on the wire (unlike the
 *  identically-named fields inside the sealed `GrantEnvelope` above) —
 *  that's the whole point: `fetchPairingGrant`/`fetchPairingRequestByCode`
 *  can distinguish "this slot holds a grant" from "this slot still holds a
 *  request" (`kind: 'octobot-pairing-request'`, see
 *  `identity/pairingRequest.ts`) by reading one field, before ever calling
 *  `unseal()`. */
interface JoinSessionGrantDoc {
  v: typeof GRANT_ENVELOPE_VERSION
  kind: typeof GRANT_ENVELOPE_KIND
  sealed: SealedBlob
}

/** Phone side, step 2: seal and publish the minted grant to the request's
 *  `code` slot — this OVERWRITES the request doc still published there,
 *  since request and grant now share one address.
 *
 *  `rendezvous` is the caller's OWN trusted server config — the same one it
 *  used to look up `request` via `fetchPairingRequestByCode` — never
 *  `request.rendezvous`. That field rides inside a document anyone can
 *  publish to the public `joinsessions` collection, so trusting it here
 *  would let a malicious "website" party point this phone's outbound POST at
 *  an arbitrary host of its choosing.
 *
 *  `baseHash` MUST be the `hash` `fetchPairingRequestByCode` returned
 *  alongside `request` — this is what makes "claim this specific, exact
 *  request" atomic: the push only succeeds if the slot still holds exactly
 *  the request doc this caller read, so a request that was swapped or
 *  already claimed by someone else between the read and this write is
 *  detected as a conflict rather than silently overwritten. There is no
 *  longer a meaningful "first publish, baseHash: null" case the way the
 *  retired sessionId-keyed design had one — the slot is never empty by the
 *  time a caller reaches this function, it already holds the request. A
 *  caller legitimately RE-publishing later (a refresh) must pass back the
 *  hash THIS function returned from its own previous call. Returns the
 *  resulting hash for exactly that purpose. */
export async function publishPairingGrant(opts: {
  request: PairingRequestPayload
  sealer: SealerKeys
  grant: MintedPairingGrant
  rendezvous: { baseUrl: string; namespace: string }
  baseHash: string | null
  fetch?: typeof fetch
  timeoutMs?: number
}): Promise<{ hash: string }> {
  const client = createRendezvousClient({
    baseUrl: opts.rendezvous.baseUrl,
    namespace: opts.rendezvous.namespace,
    fetch: opts.fetch,
    timeoutMs: opts.timeoutMs,
  })
  try {
    const envelope: GrantEnvelope = {
      v: GRANT_ENVELOPE_VERSION,
      kind: GRANT_ENVELOPE_KIND,
      bundle: opts.grant.bundle,
    }
    const plaintext = new TextEncoder().encode(JSON.stringify(envelope))
    const sealed = await seal(plaintext, opts.request.devKemPub, opts.sealer, opts.request.code)
    const doc: JoinSessionGrantDoc = { v: GRANT_ENVELOPE_VERSION, kind: GRANT_ENVELOPE_KIND, sealed }
    return await pushRendezvousDoc(
      client, joinSessionPath(opts.request.code), doc as unknown as Record<string, unknown>, opts.baseHash,
    )
  } catch (err) {
    if (err instanceof ConflictError) {
      throw new OctoBotConflictError(
        err.currentHash || null, err,
        'pairing request slot was modified since it was read — this pairing may be compromised, or someone else already claimed it',
      )
    }
    rethrowAsOctoBotError(err)
  }
}

/** Phone side: stop publishing and clear the current slot — since request
 *  and grant share one address, this clears BOTH together (there is no way
 *  to clear one but keep the other). It stops future reads but cannot
 *  recall a grant a website already fetched — with this design, "cannot
 *  recall" is narrow: the grant itself only proves space membership, and
 *  `removeSpaceMember`-based revocation (real, immediate, checked live on
 *  every request) is the actual unpair mechanism a caller should use
 *  ALONGSIDE this, not instead of it — this only stops the CODE from
 *  resolving to a usable grant again, it does not by itself revoke a grant
 *  already handed out. */
export async function clearPairingGrant(opts: {
  request: PairingRequestPayload
  rendezvous: { baseUrl: string; namespace: string }
  fetch?: typeof fetch
  timeoutMs?: number
}): Promise<{ hash: string }> {
  const client = createRendezvousClient({
    baseUrl: opts.rendezvous.baseUrl,
    namespace: opts.rendezvous.namespace,
    fetch: opts.fetch,
    timeoutMs: opts.timeoutMs,
  })
  try {
    return await clearRendezvousDoc(client, joinSessionPath(opts.request.code))
  } catch (err) {
    rethrowAsOctoBotError(err)
  }
}

export interface UnsealedPairingGrant {
  spaceId: string
  /** Live read of every mirror collection the grant currently covers — a
   *  real pull, not a cached/point-in-time value; call `readMirrorCollections`
   *  again directly for a later refresh rather than re-fetching the grant. */
  collections: Partial<Record<MirrorCollectionId, unknown>>
  /** The Ed25519 pubkey that actually sealed this grant, verified via the
   *  wrap entry's signature (never merely claimed — `unseal` always checks
   *  it). A trust-on-first-use pin: record it after the FIRST successful
   *  call and pass it back as `expectedSealer` on every later poll for this
   *  session, so a later writer to the same slot cannot silently replace an
   *  established pairing's grant with their own. Nothing pins WHO this key
   *  belongs to on the very first read — that trust comes from the grant
   *  write itself being a compare-and-swap against the exact request hash
   *  `fetchPairingRequestByCode` returned (see `publishPairingGrant`), which
   *  only the party that actually read the live, unclaimed request could
   *  have supplied. */
  sealedBy: string
  /** The per-node grants this bundle unwrapped to — the SAME ones
   *  `readMirrorCollections` above just used to pull `collections`. Exposed
   *  so a caller can make its own authenticated calls (e.g.
   *  `attemptDirectMirrorWrite`) without re-fetching and re-unsealing the
   *  grant. Always read-only in practice: `mintPairingGrant` mints with
   *  `write: false`, so no cap here carries `'write'`. */
  nodes: MirrorGrantNodeRef[]
}

/** Website side: read whatever is currently published at this session's
 *  slot. Three outcomes:
 *  - nothing published (wrong/expired code) → `null`, "keep waiting".
 *  - still `kind: 'octobot-pairing-request'` (the phone hasn't approved
 *    yet) → also `null`, "keep waiting" — this is the normal, expected
 *    state for most of the polling loop's life, NOT an error.
 *  - `kind: 'octobot-pairing-grant'` → unseal it and immediately do a live
 *    read of every mirror collection it covers.
 *  Anything else (an unrecognized `kind`, or a `kind: 'octobot-pairing-grant'`
 *  doc whose `sealed` field isn't actually a sealed blob) throws — that's a
 *  genuine malformed-document case, not a wait state. */
export async function fetchPairingGrant(
  session: { code: string; device: GeneratedDeviceKeys; rendezvous: { baseUrl: string; namespace: string } },
  opts: { expectedSealer?: string; fetch?: typeof fetch; timeoutMs?: number } = {},
): Promise<UnsealedPairingGrant | null> {
  const client = createRendezvousClient({
    baseUrl: session.rendezvous.baseUrl,
    namespace: session.rendezvous.namespace,
    fetch: opts.fetch,
    timeoutMs: opts.timeoutMs,
  })
  const doc = await pullRendezvousDoc(client, joinSessionPath(session.code))
  if (!doc) return null
  const data = doc.data as Record<string, unknown>
  if (data.kind === 'octobot-pairing-request') return null
  if (data.v !== GRANT_ENVELOPE_VERSION || data.kind !== GRANT_ENVELOPE_KIND) {
    throw new Error('pairing grant: unrecognized document at this code\'s slot')
  }
  if (typeof data.sealed !== 'object' || data.sealed === null || typeof (data.sealed as Record<string, unknown>).entry !== 'object' || (data.sealed as Record<string, unknown>).entry === null) {
    throw new Error('pairing grant: malformed sealed blob at this code\'s slot')
  }
  const sealed = data.sealed as unknown as SealedBlob
  const plaintext = await unseal(sealed, session.device.kemPriv, {
    aad: session.code,
    ...(opts.expectedSealer !== undefined ? { requireSealer: opts.expectedSealer } : {}),
  })
  const envelopeRaw: unknown = JSON.parse(new TextDecoder().decode(plaintext))
  if (
    typeof envelopeRaw !== 'object' || envelopeRaw === null
    || (envelopeRaw as Record<string, unknown>).v !== GRANT_ENVELOPE_VERSION
    || (envelopeRaw as Record<string, unknown>).kind !== GRANT_ENVELOPE_KIND
    || typeof (envelopeRaw as Record<string, unknown>).bundle !== 'string'
  ) {
    throw new Error('pairing grant: malformed grant envelope')
  }
  const { spaceId, nodes } = parseMirrorGrantBundle((envelopeRaw as GrantEnvelope).bundle)
  const sealedBy = sealed.entry.addedBy
  const collections = await readMirrorCollections({
    rendezvous: session.rendezvous,
    spaceId,
    nodes,
    devEdPrivHex: session.device.edPriv,
    devKemPrivHex: session.device.kemPriv,
    fetch: opts.fetch,
    timeoutMs: opts.timeoutMs,
  })
  return { spaceId, collections, sealedBy, nodes }
}

/** Website side: poll until the phone's FIRST approval publishes a grant,
 *  or `timeoutMs` elapses. This is the initial-approval wait, not an ongoing
 *  refresh loop — for later refreshes call `readMirrorCollections` directly.
 *
 *  A `fetchPairingGrant` failure (a network blip, a transient server error)
 *  does NOT end the wait — it's swallowed and retried on the next tick, same
 *  as `fetchPairingGrant` returning `null` for "nothing published yet". Only
 *  reaching `deadline` ends it: with the last error if there was one (more
 *  informative than a bare timeout), else the generic timeout. */
export async function awaitPairingGrant(
  session: { code: string; device: GeneratedDeviceKeys; rendezvous: { baseUrl: string; namespace: string } },
  opts: { timeoutMs?: number; signal?: AbortSignal; fetch?: typeof fetch } = {},
): Promise<UnsealedPairingGrant> {
  const deadline = Date.now() + (opts.timeoutMs ?? 5 * 60 * 1000)
  let lastErr: unknown
  for (let attempt = 0; ; attempt++) {
    if (opts.signal?.aborted) throw new DOMException('aborted', 'AbortError')
    try {
      const result = await fetchPairingGrant(session, { fetch: opts.fetch })
      if (result) return result
    } catch (err) {
      lastErr = err
    }
    if (Date.now() >= deadline) {
      if (lastErr) rethrowAsOctoBotError(lastErr)
      throw new OctoBotConnectionError('timeout', 'timed out waiting for the pairing to be approved')
    }
    await abortableSleep(pollDelay(attempt), opts.signal)
  }
}
