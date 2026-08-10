import { ConflictError } from '@drakkar.software/starfish-client'
import type { GeneratedDeviceKeys } from '@drakkar.software/starfish-identities'
import {
  createPairingRequest,
  parsePairingRequest,
  type PairingRequestPayload,
} from '../../identity/pairingRequest.js'
import {
  createRendezvousClient,
  pullRendezvousDoc,
  pushRendezvousDoc,
  joinSessionPath,
} from '../../transport/rendezvous.js'
import { OctoBotConflictError, rethrowAsOctoBotError } from '../core/errors.js'
import type { NodeCollectionKey } from '../../collections/nodeCollections.js'

export type StartPairingRequestOptions = {
  origin: string
  rendezvous: { baseUrl: string; namespace: string }
  label?: string
  requestedCollections?: NodeCollectionKey[]
  ttlSec?: number
  /** See `PairingRequestPayload.requesterKind`. Defaults to `'website'`. */
  requesterKind?: 'website' | 'device'
  fetch?: typeof fetch
  timeoutMs?: number
}

/** A website's own end of a device-code pairing: its request record plus
 *  everything needed to publish it and later unseal the phone's response.
 *  `code` is what the site displays for the user to type into their OctoBot
 *  app — this package never renders it, just returns the string. Carries its
 *  own `rendezvous` (the same value passed to `startPairingRequest`) so
 *  `awaitPairingGrant`/`fetchPairingGrant` can take the session directly,
 *  with no re-spreading required at the call site. */
export interface PairingRequestSession {
  request: PairingRequestPayload
  device: GeneratedDeviceKeys
  code: string
  rendezvous: { baseUrl: string; namespace: string }
  /** Publish (or re-publish) the request record to the rendezvous. */
  publish(): Promise<void>
}

/**
 * Website side, step 1: create and publish a pairing request.
 *
 * ```ts
 * const rendezvous = { baseUrl: 'https://sync.drakkar.software/sync', namespace: 'dk' }
 * const session = await startPairingRequest({ origin: 'https://myapp.example', rendezvous })
 * await session.publish()
 * showCodeToUser(session.code)
 * const grant = await awaitPairingGrant(session)
 * ```
 */
export async function startPairingRequest(opts: StartPairingRequestOptions): Promise<PairingRequestSession> {
  const { request, device, code } = await createPairingRequest(opts)
  const client = createRendezvousClient({
    baseUrl: opts.rendezvous.baseUrl,
    namespace: opts.rendezvous.namespace,
    fetch: opts.fetch,
    timeoutMs: opts.timeoutMs,
  })
  // This session's own remembered hash from its last successful publish —
  // starts null (a fresh code has nothing published under it yet, so the
  // FIRST publish() is create-only: it fails rather than silently adopting
  // whatever's already occupying the slot). Every later publish() call uses
  // its own remembered hash instead of re-pulling and trusting whatever the
  // server currently reports, so a hostile overwrite between two publish()
  // calls surfaces as a loud conflict instead of silently becoming this
  // session's new baseline.
  let lastHash: string | null = null
  // Serializes overlapping publish() calls on the SAME session — without
  // this, two calls in flight at once both read the same lastHash before
  // either awaits, so the one the server processes second gets a real
  // ConflictError caused only by this session's own overlapping write, not
  // third-party tampering, yet (post-own-write-CAS) it hits the exact same
  // "treat this code as compromised" error a genuine hijack would.
  let queue: Promise<void> = Promise.resolve()
  async function doPublish() {
    try {
      const result = await pushRendezvousDoc(
        client, joinSessionPath(code), request as unknown as Record<string, unknown>, lastHash,
      )
      lastHash = result.hash
    } catch (err) {
      if (err instanceof ConflictError) {
        // Thrown as OctoBotConflictError directly (not wrapped in a plain
        // Error then run through rethrowAsOctoBotError) so `code === 'conflict'`
        // and `instanceof OctoBotConflictError` survive — the documented
        // "switch on code" convention callers rely on to distinguish a
        // tampered slot from a generic unreachable-node failure.
        throw new OctoBotConflictError(
          err.currentHash || null, err,
          'pairing request was modified by another party — treat this code as compromised',
        )
      }
      rethrowAsOctoBotError(err)
    }
  }
  return {
    request,
    device,
    code,
    rendezvous: opts.rendezvous,
    publish() {
      const run = queue.then(() => doPublish())
      // Swallow so a failed publish() doesn't permanently wedge the queue
      // for the NEXT caller's publish() — each call still observes its own
      // rejection via the returned promise.
      queue = run.catch(() => {})
      return run
    },
  }
}

/** The result of a request lookup: the parsed request plus the pulled
 *  document's `hash`. The hash matters — it's what the phone must pass as
 *  `baseHash` when it later mints and publishes a grant, so that write is a
 *  compare-and-swap against the EXACT request doc it read, not a blind
 *  overwrite. See `client/pairing/pairingGrantExchange.ts`'s
 *  `publishPairingGrant`. */
export interface PairingRequestLookup {
  request: PairingRequestPayload
  hash: string
}

/** Phone side, step 1: look up a request by the code the user typed. Returns
 *  `null` only when nothing is published under that code at all (wrong code,
 *  or the rendezvous slot's own TTL already reclaimed it). A request that IS
 *  still present but past its own `expiresAt` does NOT return `null` — it
 *  throws (via `parsePairingRequest`), so the caller can tell "wrong code"
 *  apart from "right code, but it expired" and say so accurately. If the
 *  slot has ALREADY moved past the request phase (a grant is published
 *  there — `kind === 'octobot-pairing-grant'`, detectable without unsealing
 *  anything, see `pairingGrantExchange.ts`), this throws a distinct
 *  `OctoBotConflictError` rather than a generic parse failure, so a caller
 *  re-checking an already-approved code gets an accurate "already used"
 *  signal instead of "malformed pairing request payload". */
export async function fetchPairingRequestByCode(opts: {
  code: string
  rendezvous: { baseUrl: string; namespace: string }
  fetch?: typeof fetch
  timeoutMs?: number
}): Promise<PairingRequestLookup | null> {
  const client = createRendezvousClient({
    baseUrl: opts.rendezvous.baseUrl,
    namespace: opts.rendezvous.namespace,
    fetch: opts.fetch,
    timeoutMs: opts.timeoutMs,
  })
  try {
    const doc = await pullRendezvousDoc(client, joinSessionPath(opts.code))
    if (!doc) return null
    if (doc.data.kind === 'octobot-pairing-grant') {
      throw new OctoBotConflictError(doc.hash, undefined, 'this code has already been used to complete a pairing')
    }
    const request = parsePairingRequest(JSON.stringify(doc.data), opts.code)
    return { request, hash: doc.hash }
  } catch (err) {
    if (err instanceof OctoBotConflictError) throw err
    rethrowAsOctoBotError(err)
  }
}

/** Shared by `pairingGrantExchange.ts`'s polling loops — keep the
 *  abort/timeout/cleanup semantics in exactly one place. */
export function abortableSleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(new DOMException('aborted', 'AbortError'))
    const timer = setTimeout(resolve, ms)
    signal?.addEventListener('abort', () => {
      clearTimeout(timer)
      reject(new DOMException('aborted', 'AbortError'))
    })
  })
}
