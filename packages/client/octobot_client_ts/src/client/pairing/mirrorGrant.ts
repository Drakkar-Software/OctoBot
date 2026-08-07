import {
  inviteToSpace,
  readObjectTree,
  removeSpaceMember,
  type Session,
} from '@drakkar.software/starfish-spaces'
import { defaultUserIdFromEdPub } from '@drakkar.software/starfish-spaces'
import type { PairingRequestPayload } from '../../identity/pairingRequest.js'
import {
  findOrCreateMirrorSpace,
  isKnownMirrorCollection,
  isThirdPartyEligible,
  MIRROR_SPACE_SHARED_NAME,
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

export interface MintedPairingGrant {
  /** The JSON-stringified space-invite bundle `inviteToSpace` returns —
   *  `{spaceId, spaceName, cap}`. `cap` is a real `space:member` cap: it
   *  grants read access to EVERY currently-enabled collection in the SHARED
   *  mirror space (never the private one, and never `user-accounts-auth`,
   *  which the mirror doesn't write to any space at all — see
   *  `mirror/collections.ts`), because that's what a space-member grant
   *  means. `mintPairingGrant` uses `inviteToSpace`, not the per-node
   *  `inviteToNode`: `getNodeAccess` resolves `access:'invite'` nodes
   *  through an isolated PER-NODE keyring nothing here seeds, while
   *  `access:'space'` nodes (what `mirror/writer.ts` actually creates) are
   *  gated by space membership and encrypted under the one space-wide
   *  keyring — confirmed against the installed SDK source after hitting a
   *  real "no keyring yet" failure with the per-node approach. */
  bundle: string
  spaceId: string
  /** `defaultUserIdFromEdPub(request.devEdPub)` — the space-member identity
   *  `inviteToSpace` just registered in the space's `_access.members` list.
   *  Callers keep this so `unpairWebsite`-style revocation can call
   *  `removeSpaceMember(client, spaceId, memberUserId, session)` later
   *  without re-deriving it (or needing the original `request` again). */
  memberUserId: string
  /** Every third-party-eligible collection the shared mirror space actually
   *  had a node for at mint time — i.e. what this grant, being space-wide,
   *  really covers right now. Purely informational (e.g. "this site can
   *  read: accounts, automations" on a paired-sites screen); a caller that
   *  needs a live answer later should re-derive it, this is a snapshot. */
  coveredCollections: MirrorCollectionId[]
}

/**
 * Phone side: mint a read-only grant for a paired website. Invites the
 * website's own ephemeral device (from its pairing request) into the SHARED
 * mirror space as a read-only member — never the private one, and never
 * `user-accounts-auth` (which the mirror doesn't write to any space at all,
 * see `mirror/collections.ts`).
 *
 * Requires at least one third-party-eligible collection to already have a
 * mirror node (i.e. `syncCloudMirror` must have run at least once with that
 * collection enabled) — there is nothing worth inviting the website to read
 * otherwise. Throws `NothingToShareError` in that case rather than minting
 * a grant into an empty space (the invite itself would still be a real,
 * working space-member grant even with zero nodes — this check exists for
 * UX, not because `inviteToSpace` requires it).
 */
export async function mintPairingGrant(
  session: Session,
  request: PairingRequestPayload,
): Promise<MintedPairingGrant> {
  const joinRequestJson = await buildJoinRequestJson(request)
  const space = await findOrCreateMirrorSpace(session, MIRROR_SPACE_SHARED_NAME)
  const tree = await readObjectTree(session, space.id)
  const hasShareableCollection = tree.some(
    (node) => isKnownMirrorCollection(node.type) && isThirdPartyEligible(node.type),
  )
  if (!hasShareableCollection) throw new NothingToShareError()
  const bundle = await inviteToSpace(session, space.id, joinRequestJson, false)
  const memberUserId = await defaultUserIdFromEdPub(request.devEdPub)
  const coveredCollections = tree
    .filter((node) => isKnownMirrorCollection(node.type) && isThirdPartyEligible(node.type))
    .map((node) => node.type as MirrorCollectionId)
  return { bundle, spaceId: space.id, memberUserId, coveredCollections }
}

/**
 * Phone side: revoke a previously-minted grant by removing the paired
 * website's ephemeral device from the shared mirror space's member roster
 * (`_access.members`) — the live, TOFU-checked list `space:member`-gated
 * reads (objdoc's `read_roles`) actually consult on every request. This
 * is real, immediate revocation: the next read the site attempts 403s, it
 * does not depend on the (confirmed-unreachable-on-the-deployed-server, see
 * the space-mirror design's Infra findings) cap-revocation-list plumbing.
 *
 * The one honest residual: this cannot erase what the site already fetched
 * and decrypted before this call — same caveat every revocation design in
 * this package documents.
 */
export async function revokePairingGrant(session: Session, spaceId: string, memberUserId: string): Promise<void> {
  await removeSpaceMember(session.spacesRegistryClient, spaceId, memberUserId, session)
}
