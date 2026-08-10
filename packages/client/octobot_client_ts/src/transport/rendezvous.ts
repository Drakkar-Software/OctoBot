import { StarfishClient, ConflictError } from '@drakkar.software/starfish-client'
import { createTimeoutFetch } from './syncClient.js'
import { pullPath, pushPath } from '../collections/paths.js'
import { SYNC_FETCH_TIMEOUT_MS } from '../crypto/wireConstants.js'

const MAX_PUSH_RETRIES = 3

/** Storage path for a device-code pairing exchange — must match the
 *  `joinsessions` collection's `storagePath` template
 *  (`_pairing/session/{code}`, defined in
 *  `Infra/sync/server/drakkar_sync/apps/dk_spaces/collections.py`). ONE
 *  address serves BOTH phases of the exchange: the website's discovery
 *  "request" doc, and the phone's delivery "grant" doc that later overwrites
 *  it — keyed throughout by the same short human-typeable `code` (see
 *  `client/pairing/pairingRequest.ts` and `pairingGrantExchange.ts` for how
 *  the two phases are told apart on the wire). Replaces the retired
 *  two-collection, two-address design (`pairingrequests`/`pairingsnapshots`,
 *  a low-entropy code address plus a separate high-entropy session
 *  address) — that split bought no real confidentiality the grant's own
 *  sealing didn't already provide, only lifecycle bookkeeping this merge no
 *  longer needs. */
export function joinSessionPath(code: string): string {
  return `_pairing/session/${encodeURIComponent(code)}`
}

export interface RendezvousDoc {
  data: Record<string, unknown>
  hash: string
}

/** A cap-less `StarfishClient` against a public rendezvous collection — a
 *  different namespace/host from the node client `createSyncClient` builds
 *  (the rendezvous lives on the shared Drakkar sync server, not the user's
 *  own node), and deliberately carries no `capProvider`: every request is
 *  anonymous, matching the deployed `joinsessions` collection's `public`
 *  read/write roles. */
export function createRendezvousClient(opts: {
  baseUrl: string
  namespace: string
  fetch?: typeof fetch
  timeoutMs?: number
}): StarfishClient {
  return new StarfishClient({
    baseUrl: opts.baseUrl,
    namespace: opts.namespace,
    fetch: createTimeoutFetch(opts.timeoutMs ?? SYNC_FETCH_TIMEOUT_MS, opts.fetch ?? globalThis.fetch),
  })
}

/** Pull a rendezvous document. Returns `null` when nothing has been
 *  published to this slot yet — an unwritten collection document pulls with
 *  `data` as the STRING `"null"` (an observed real node's behavior for the
 *  standard collection pull path; this rendezvous server is a different,
 *  not-yet-deployed deployment, so a raw `null` or an empty `{}` are handled
 *  too rather than assumed away), not a 404 — so a nullish/empty `data` is
 *  the actual not-found signal here, not a thrown error. */
export async function pullRendezvousDoc(client: StarfishClient, path: string): Promise<RendezvousDoc | null> {
  const result = await client.pull(pullPath(path, {}))
  const parsed: unknown = typeof result.data === 'string' ? JSON.parse(result.data) : result.data
  if (parsed == null || typeof parsed !== 'object' || Array.isArray(parsed)) return null
  if (Object.keys(parsed).length === 0) return null
  return { data: parsed as Record<string, unknown>, hash: result.hash }
}

/** Push a rendezvous document against an EXPLICIT `baseHash` — the caller's
 *  OWN remembered hash from its last successful write to this path, or
 *  `null` for a genuinely fresh slot nothing has been published to yet.
 *  Reimplements what `starfish-identities`' `pushPairingBundle` does
 *  internally, because that helper is hard-typed to a `PairingBundle` shape
 *  (`{capCert, rootEdPub, wrappedCEKs}`) this package's rendezvous documents
 *  don't have, and its sibling `fetchPairingBundle` returns `null` for
 *  anything without a top-level `capCert` — a document shaped like ours
 *  would never be recognized by it.
 *
 *  Deliberately does NOT re-pull and adopt whatever's currently at `path` on
 *  a conflict (the previous version of this function did exactly that,
 *  retrying against the server's current hash) — that behavior is what let
 *  a hostile overwrite of this slot go undetected forever, including by the
 *  original publisher's own next write, which would silently treat the
 *  attacker's content as the new legitimate baseline. A `ConflictError` here
 *  means the document changed since THIS CALLER last wrote it, which the
 *  caller should treat as "this slot may have been tampered with", not
 *  retry past. Returns the resulting hash so the caller can remember it for
 *  its next write.
 *
 *  This is still inherently last-write-wins at the slot level, not
 *  first-writer-wins — a concurrent anonymous writer who wins the race for
 *  a GENUINELY fresh slot (`baseHash: null`) is indistinguishable from the
 *  legitimate first writer. The defense against that is the human-typeable
 *  `code`'s entropy plus the collection's per-IP rate limit, which bound how
 *  fast an unknown code can be guessed — NOT address secrecy (this
 *  collection is public-read, so anyone who knows or guesses a code can
 *  read whatever is currently published there regardless of write history).
 *  What THIS change adds is detecting tampering on every write AFTER the
 *  first, which the previous blind-retry behavior could never do because it
 *  always treated "conflict" as "let me just adopt whatever's there now".
 *  It does NOT stop a writer who first PULLS the slot (learning its current
 *  hash, which is public information) and then pushes with that hash as
 *  `baseHash` — that is a legitimate-looking, non-blind overwrite as far as
 *  this primitive is concerned; the real protection against that shape of
 *  attack is `code`-bound `popSig` verification (see
 *  `identity/pairingRequest.ts`) rejecting any replacement request that
 *  isn't signed by keys the ORIGINAL requester controls, and the grant
 *  phase's own `baseHash` CAS against the exact request hash it read. */
export async function pushRendezvousDoc(
  client: StarfishClient,
  path: string,
  data: Record<string, unknown>,
  baseHash: string | null,
): Promise<{ hash: string }> {
  return client.push(pushPath(path, {}), data, baseHash)
}

/** Overwrite a slot with an empty document, regardless of its current
 *  content — the one place blind-overwrite-and-retry semantics are still
 *  correct: unpair/cleanup must succeed even without a remembered hash
 *  (e.g. in-memory state was lost across a page reload), and "did someone
 *  else already overwrite this" isn't a meaningful question when the
 *  caller's whole intent is "nothing should be published here anymore".
 *  The deployed `joinsessions` collection's `ttl_ms` is an outer backstop,
 *  not a substitute for actually clearing on unpair — see the Infra
 *  collection's doc comment. Because request and grant now share one
 *  address, clearing this slot clears BOTH the original request and any
 *  published grant together — there's no way to clear one but keep the
 *  other.
 *
 *  Deliberately pulls the RAW `client.pull()` result here, not
 *  `pullRendezvousDoc` — that function collapses an existing-but-empty doc
 *  (`{}`, which is exactly what THIS function itself writes) down to `null`,
 *  discarding its real hash. Deriving `baseHash` from that collapsed `null`
 *  would push `baseHash: null` against a slot that DOES have a hash — a
 *  guaranteed conflict, identically, on every one of the retries below.
 *  That made clearing an already-cleared slot (a benign double-unpair, or
 *  the very recovery path this package documents: unpair then re-approve)
 *  permanently fail. The raw hash exists whether or not the data is
 *  "empty", so blind-overwrite-and-retry works correctly in every case.
 *
 *  Returns the resulting hash — same shape as `pushRendezvousDoc` — so a
 *  caller that legitimately needs to publish again right after clearing
 *  (e.g. re-approving the same session) can use it as its next `baseHash`
 *  instead of `null`, which would otherwise conflict against the very
 *  document this call just wrote. */
export async function clearRendezvousDoc(client: StarfishClient, path: string): Promise<{ hash: string }> {
  let lastConflict: ConflictError | undefined
  for (let attempt = 0; attempt < MAX_PUSH_RETRIES; attempt++) {
    const current = await client.pull(pullPath(path, {}))
    try {
      return await client.push(pushPath(path, {}), {}, current.hash)
    } catch (err) {
      if (!(err instanceof ConflictError)) throw err
      lastConflict = err
    }
  }
  throw new Error(`clearRendezvousDoc: too many baseHash conflicts at ${path}`, { cause: lastConflict })
}
