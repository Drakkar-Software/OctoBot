import {
  inviteToNode,
  readObjectTree,
  removeNodeKeyringRecipient,
  type Session,
} from '@drakkar.software/starfish-spaces'
import { defaultUserIdFromEdPub } from '@drakkar.software/starfish-spaces'
import type { CapCert } from '@drakkar.software/starfish-protocol'
import type { PairingRequestPayload } from '../../identity/pairingRequest.js'
import {
  findOrCreateMirrorSpace,
  isIsolatedMirrorCollection,
  isKnownMirrorCollection,
  MIRROR_SPACE_NAME,
  type MirrorCollectionId,
} from '../mirror/index.js'

/**
 * Rebuild the `{edPub, kemPub, userId, kemSig}` "join request" JSON
 * `starfish-spaces`' `inviteToNode`/`parseJoinRequest` expect, from a
 * `PairingRequestPayload`'s already-public `devEdPub`/`devKemPub` plus the
 * `joinRequestKemSig` it carries. The website computes `joinRequestKemSig`
 * once (via `signKemSig`) when it generates its ephemeral device keys in
 * `startPairingRequest` — this just reassembles the same shape
 * `makeJoinRequest(session)` would have produced, without the website ever
 * needing a full `starfish-spaces` `Session` for an identity it has no
 * wallet to derive (it's a website, not a wallet holder).
 */
export async function buildJoinRequestJson(request: PairingRequestPayload): Promise<string> {
  const userId = await defaultUserIdFromEdPub(request.devEdPub)
  return JSON.stringify({
    edPub: request.devEdPub,
    kemPub: request.devKemPub,
    userId,
    kemSig: request.joinRequestKemSig,
  })
}

export class NothingToShareError extends Error {
  constructor() {
    super('cloud sync: nothing enabled to share yet — enable at least one collection before pairing')
    this.name = 'NothingToShareError'
  }
}

/** One granted collection, as the website needs it to read that node: the two
 *  caps `inviteToNode(..., {isolated: true})` mints — `contentCap` (`objinv`)
 *  to fetch the document, `keyringCap` (`nodekeyring`) to open it. */
export interface MirrorGrantNode {
  collectionId: MirrorCollectionId
  nodeId: string
  contentCap: CapCert
  keyringCap: CapCert
}

/** The grant document, published sealed through the pairing rendezvous. `v`
 *  is a wire version: a website built against the old space-member grant sees
 *  a shape it cannot parse and must say so, rather than silently reading
 *  nothing. */
export interface MirrorGrantDoc {
  v: 1
  spaceId: string
  nodes: MirrorGrantNode[]
}

export interface MintedPairingGrant {
  /** JSON-stringified `MirrorGrantDoc`. One grant per collection, each
   *  reaching exactly one node — never the whole space. */
  bundle: string
  spaceId: string
  /** `defaultUserIdFromEdPub(request.devEdPub)`. The website is NOT added to
   *  the space roster (that is the point of the isolated tier), so this is an
   *  identifier for bookkeeping, not a membership record. */
  memberUserId: string
  /** The website's ephemeral KEM pubkey — the recipient entry
   *  `revokePairingGrant` removes from each node's keyring. */
  memberKemPub: string
  /** Exactly what this grant covers. Unlike the old space-wide grant this is
   *  not a snapshot that can silently widen: a collection enabled later gets
   *  no grant until the user pairs again. */
  coveredCollections: MirrorCollectionId[]
}

/**
 * Phone side: mint a read-only grant for a paired website — one per-node
 * invite for each currently-mirrored, third-party-eligible collection.
 *
 * The website joins no space roster. Each invite carries a cap for that one
 * node's content plus a recipient slot in that one node's keyring, so the
 * grant reaches exactly the collections shown in the pairing UI and nothing
 * else — `user-settings` (`visibility: "private"`, space keyring) and
 * `user-accounts-auth` (never mirrored at all) are unreachable by
 * construction rather than by policy.
 *
 * Throws `NothingToShareError` when no eligible collection has a mirror node
 * yet (i.e. `syncCloudMirror` has not run with one enabled).
 */
export async function mintPairingGrant(
  session: Session,
  request: PairingRequestPayload,
): Promise<MintedPairingGrant> {
  const joinRequestJson = await buildJoinRequestJson(request)
  const space = await findOrCreateMirrorSpace(session, MIRROR_SPACE_NAME)
  const tree = await readObjectTree(session, space.id)
  const grantable = tree.filter(
    (node) => isKnownMirrorCollection(node.type) && isIsolatedMirrorCollection(node.type),
  )
  if (grantable.length === 0) throw new NothingToShareError()

  const nodes: MirrorGrantNode[] = []
  for (const node of grantable) {
    // `isolated: true` is what keeps this off the space roster and off the
    // space keyring; `write: false` is what makes it read-only.
    const bundleJson = await inviteToNode(
      session,
      space.id,
      node.id,
      joinRequestJson,
      { enc: true },
      node.type,
      { isolated: true, write: false },
    )
    const bundle = JSON.parse(bundleJson) as { nodeCap?: CapCert; keyringCap?: CapCert }
    if (!bundle.nodeCap || !bundle.keyringCap) {
      throw new Error(`pairing grant: incomplete invite bundle for ${node.type}`)
    }
    nodes.push({
      collectionId: node.type as MirrorCollectionId,
      nodeId: node.id,
      contentCap: bundle.nodeCap,
      keyringCap: bundle.keyringCap,
    })
  }

  const doc: MirrorGrantDoc = { v: 1, spaceId: space.id, nodes }
  return {
    bundle: JSON.stringify(doc),
    spaceId: space.id,
    memberUserId: await defaultUserIdFromEdPub(request.devEdPub),
    memberKemPub: request.devKemPub,
    coveredCollections: nodes.map((n) => n.collectionId),
  }
}

/**
 * Phone side: revoke a previously-minted grant by removing the website's
 * ephemeral KEM key from each granted node's keyring, which also rotates that
 * keyring to a new epoch. Everything written afterwards is sealed to an epoch
 * the site is not a recipient of.
 *
 * Two honest caveats, both inherent to the model rather than to this code.
 * The site keeps a valid `objinv` cap, so it can still FETCH those nodes'
 * bytes — it simply cannot decrypt anything written after this call; making
 * the fetch itself fail needs the cap-revocation-list plumbing, which is not
 * reachable on the deployed server (same finding the space-member design
 * recorded). And this cannot erase what the site already fetched and
 * decrypted — the caveat every revocation design in this package documents.
 *
 * Per-node, unlike the space-member grant it replaces: revoking one
 * collection leaves the others working.
 */
export async function revokePairingGrant(
  session: Session,
  spaceId: string,
  nodeIds: readonly string[],
  memberKemPub: string,
): Promise<void> {
  for (const nodeId of nodeIds) {
    await removeNodeKeyringRecipient(session, spaceId, nodeId, [memberKemPub])
  }
}
