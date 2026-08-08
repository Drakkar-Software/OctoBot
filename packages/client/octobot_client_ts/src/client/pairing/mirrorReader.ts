import type { CapCert, PushSuccess } from '@drakkar.software/starfish-protocol'
import { readIsolatedSpaceMirror } from '@drakkar.software/starfish-replica/space'
import { StarfishClient, type StarfishCapProvider } from '@drakkar.software/starfish-client'
import { createTimeoutFetch } from '../../transport/syncClient.js'
import { SYNC_FETCH_TIMEOUT_MS } from '../../crypto/wireConstants.js'
import { isKnownMirrorCollection, mirrorDocPushPath, mirrorDocPath, type MirrorCollectionId } from '../mirror/index.js'

/** The grant document `mintPairingGrant` publishes (sealed) and this module
 *  unpacks: one entry per granted collection, each naming the node and the
 *  two caps that reach it. The node list is carried IN the grant because a
 *  per-node grant holder cannot read `objindex` to discover it. */
export interface MirrorGrantBundle {
  spaceId: string
  nodes: MirrorGrantNodeRef[]
}

export interface MirrorGrantNodeRef {
  collectionId: MirrorCollectionId
  nodeId: string
  contentCap: CapCert
  keyringCap: CapCert
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
  // A pre-per-node grant (one space-wide `cap`, no `nodes`) is not something
  // this reader can silently treat as "nothing shared" — say so instead.
  if (!Array.isArray(b.nodes)) {
    throw new Error('pairing grant: missing nodes — this grant was issued by an older, incompatible version')
  }
  const nodes = b.nodes.map((raw, i) => {
    const n = raw as Record<string, unknown>
    if (typeof n?.collectionId !== 'string' || typeof n?.nodeId !== 'string') {
      throw new Error(`pairing grant: malformed node at index ${i}`)
    }
    if (typeof n.contentCap !== 'object' || n.contentCap === null) {
      throw new Error(`pairing grant: node ${n.collectionId} is missing its content cap`)
    }
    if (typeof n.keyringCap !== 'object' || n.keyringCap === null) {
      throw new Error(`pairing grant: node ${n.collectionId} is missing its keyring cap`)
    }
    return {
      collectionId: n.collectionId as MirrorCollectionId,
      nodeId: n.nodeId,
      contentCap: n.contentCap as CapCert,
      keyringCap: n.keyringCap as CapCert,
    }
  })
  return { spaceId: b.spaceId, nodes }
}

export interface ReadMirrorCollectionsOptions {
  rendezvous: { baseUrl: string; namespace: string }
  spaceId: string
  /** From `parseMirrorGrantBundle` — exactly the nodes this grant covers. */
  nodes: readonly MirrorGrantNodeRef[]
  /** The website's own ephemeral Ed25519 private key (hex) — from the same
   *  `device` the site generated in `startPairingRequest`; every cap was
   *  minted for exactly this device's pubkey. */
  devEdPrivHex: string
  /** The website's own ephemeral X25519 KEM private key (hex) — same `device`
   *  as `devEdPrivHex`. Each `inviteToNode` added this device's KEM pubkey as
   *  a recipient of THAT node's own keyring; content is sealed under those,
   *  not under the caps. */
  devKemPrivHex: string
  fetch?: typeof fetch
  timeoutMs?: number
}

/**
 * Website side, session-less: pull every collection the grant covers. A REAL
 * live read, not a point-in-time export — call it again any time to see the
 * latest write, bounded only by how often the wallet's writer refreshes.
 *
 * A collection whose node was cleared (the user disabled it) or whose keyring
 * recipient was removed (the user revoked it) simply won't appear, so this
 * reflects CURRENT state rather than a snapshot of grant time.
 *
 * A thin adapter over `starfish-replica/space`'s `readIsolatedSpaceMirror`;
 * this module owns only the `mirrorDocPath` template and the timeout-wrapped
 * fetch.
 */
export async function readMirrorCollections(
  opts: ReadMirrorCollectionsOptions,
): Promise<Partial<Record<MirrorCollectionId, unknown>>> {
  return readIsolatedSpaceMirror({
    rendezvous: opts.rendezvous,
    spaceId: opts.spaceId,
    nodes: opts.nodes.filter((n) => isKnownMirrorCollection(n.collectionId)),
    devEdPrivHex: opts.devEdPrivHex,
    devKemPrivHex: opts.devKemPrivHex,
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
