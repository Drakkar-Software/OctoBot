import type { CapCert, PushSuccess } from '@drakkar.software/starfish-protocol'
import { readSpaceMirror } from '@drakkar.software/starfish-replica/space'
import { StarfishClient, type StarfishCapProvider } from '@drakkar.software/starfish-client'
import { createTimeoutFetch } from '../../transport/syncClient.js'
import { SYNC_FETCH_TIMEOUT_MS } from '../../crypto/wireConstants.js'
import { isKnownMirrorCollection, mirrorDocPushPath, mirrorDocPath, type MirrorCollectionId } from '../mirror/index.js'

/** The `NodeInviteBundle` JSON `mintPairingGrant` publishes (sealed) and this
 *  module unpacks — the fields this reader actually needs, kept narrow
 *  rather than importing `starfish-spaces`' full type (which also has
 *  fields — `nodeCap`, `streamCap`, `keyringCap` — this flow never sets,
 *  see `mintPairingGrant`'s doc comment on why it's always `kind:'space-enc'`). */
export interface MirrorGrantBundle {
  spaceId: string
  cap: CapCert
}

export function parseMirrorGrantBundle(bundleJson: string): MirrorGrantBundle {
  let parsed: unknown
  try {
    parsed = JSON.parse(bundleJson)
  } catch {
    throw new Error('pairing grant: bundle is not valid JSON')
  }
  if (typeof parsed !== 'object' || parsed === null) throw new Error('pairing grant: malformed bundle')
  const b = parsed as Record<string, unknown>
  if (typeof b.spaceId !== 'string' || !b.spaceId) throw new Error('pairing grant: missing spaceId')
  if (typeof b.cap !== 'object' || b.cap === null) throw new Error('pairing grant: missing cap')
  return { spaceId: b.spaceId, cap: b.cap as CapCert }
}

export interface ReadMirrorCollectionsOptions {
  rendezvous: { baseUrl: string; namespace: string }
  spaceId: string
  cap: CapCert
  /** The website's own ephemeral Ed25519 private key (hex) — from the same
   *  `device` the site generated in `startPairingRequest`; the cap was
   *  minted for exactly this device's pubkey. */
  devEdPrivHex: string
  /** The website's own ephemeral X25519 KEM private key (hex) — same
   *  `device` as `devEdPrivHex`. `inviteToSpace` added this device's KEM
   *  pubkey (`request.devKemPub`) as a recipient of the space's ONE
   *  keyring; this is what lets THIS reader open that keyring itself
   *  (mirrordoc content is sealed under it, not under the cap). */
  devKemPrivHex: string
  fetch?: typeof fetch
  timeoutMs?: number
}

/**
 * Website side, session-less: pull every currently-enabled mirror
 * collection the grant covers. A REAL live read, not a point-in-time
 * export — call this again any time to see the latest write, bounded only
 * by how often the wallet's writer refreshes (itself gated by the
 * `cloudSyncEnabled` setting). Returns only collections the space actually
 * has a node for; a collection disabled since the grant was minted simply
 * won't appear (its node was cleared, not deleted — see the writer's
 * clear-on-disable — so this reflects the CURRENT state honestly, not a
 * stale snapshot of what existed at grant time).
 *
 * A thin adapter over `@drakkar.software/starfish-replica/space`'s
 * `readSpaceMirror` — this module owns only the OctoBot-specific
 * `isKnownMirrorCollection` filter, `mirrorDocPath` template, and the
 * timeout-wrapped fetch; the actual pull/decrypt mechanics live upstream.
 */
export async function readMirrorCollections(
  opts: ReadMirrorCollectionsOptions,
): Promise<Partial<Record<MirrorCollectionId, unknown>>> {
  return readSpaceMirror({
    rendezvous: opts.rendezvous,
    spaceId: opts.spaceId,
    cap: opts.cap,
    devEdPrivHex: opts.devEdPrivHex,
    devKemPrivHex: opts.devKemPrivHex,
    isKnownCollection: isKnownMirrorCollection,
    docPath: mirrorDocPath,
    fetch: createTimeoutFetch(opts.timeoutMs ?? SYNC_FETCH_TIMEOUT_MS, opts.fetch ?? globalThis.fetch),
  })
}

/** Returns the SAME `{cap, devEdPrivHex}` on every call — a paired website
 *  holds one grant for one ephemeral device, never rotates it, so there is
 *  nothing to refresh. Shared shape between the write attempt below and
 *  `readSpaceMirror`'s own private cap provider (that one lives inside
 *  `starfish-replica` and isn't exported, so this is a narrow duplicate, not
 *  a reused import). */
class StaticMirrorCapProvider implements StarfishCapProvider {
  constructor(
    private readonly cap: CapCert,
    private readonly devEdPrivHex: string,
  ) {}
  async getCap(): Promise<{ cap: CapCert; devEdPrivHex: string }> {
    return { cap: this.cap, devEdPrivHex: this.devEdPrivHex }
  }
}

export interface AttemptDirectMirrorWriteOptions {
  rendezvous: { baseUrl: string; namespace: string }
  spaceId: string
  cap: CapCert
  /** The website's own ephemeral Ed25519 private key (hex) — same device the
   *  cap was minted for. */
  devEdPrivHex: string
  /** Which mirror collection to target, e.g. `'user-data'` (automations) or
   *  `'user-accounts'`. */
  collectionId: MirrorCollectionId
  /** A fresh node id — this always targets a node that does not exist yet,
   *  matching "write a new automation/account", not an edit of one that's
   *  already there. */
  nodeId: string
  /** Plain (unsealed) JSON body to push. Since the grant is expected to be
   *  read-only, the request is rejected before content ever matters — this
   *  never needs to be a validly-sealed document. */
  doc: Record<string, unknown>
  fetch?: typeof fetch
  timeoutMs?: number
}

/**
 * Website side, session-less: try to write a brand-new node directly into
 * the paired mirror space, using nothing but the grant `mintPairingGrant`
 * already handed this site (`opts.cap` + `opts.devEdPrivHex` — the exact
 * credentials `readMirrorCollections` reads with). No session, no
 * `addObject`/index update — just one raw `push` at the collection's own
 * path, the smallest possible probe of what the cap actually authorizes.
 *
 * **This call is expected to fail.** `mintPairingGrant` always mints with
 * `canWrite: false` (see `mirrorGrant.ts`), so the cap's `ops` is
 * `['read', 'list']` — no `'write'` — and the server rejects the push before
 * looking at the body. That is the point of exposing this: a paired website
 * holding only a read grant cannot unilaterally create or change anything in
 * the user's node. Making a change requires asking the user (the phone,
 * which holds the actual writable session) to approve it and publish the
 * write itself — this function is not, and is never meant to become, a
 * second write path around that approval.
 *
 * Returns the server's raw response on the (unexpected) chance it succeeds,
 * or rethrows the `StarfishHttpError` (or plain fetch failure) so a caller
 * can show the real rejection rather than a synthesized one.
 */
export async function attemptDirectMirrorWrite(
  opts: AttemptDirectMirrorWriteOptions,
): Promise<PushSuccess> {
  const client = new StarfishClient({
    baseUrl: opts.rendezvous.baseUrl,
    namespace: opts.rendezvous.namespace,
    fetch: createTimeoutFetch(opts.timeoutMs ?? SYNC_FETCH_TIMEOUT_MS, opts.fetch ?? globalThis.fetch),
    capProvider: new StaticMirrorCapProvider(opts.cap, opts.devEdPrivHex),
  })
  const path = mirrorDocPushPath(opts.collectionId, opts.spaceId, opts.nodeId)
  return client.push(path, opts.doc, null)
}
