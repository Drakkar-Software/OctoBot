/**
 * Node collections the space-mirror can offer — the canonical definition this
 * feature's per-platform copies (mobile2's `cloudSyncCollections.ts`, the node
 * web UI's `cloud-sync-collections.ts`) are meant to eventually source from
 * instead of duplicating. Ids are the SAME wire collection names the node's own
 * sync layer uses (`wire-contract.md`'s `Collections` enum values).
 *
 * `visibility` is who can ever reach a collection's mirrored copy:
 *
 * - `"private"` — the wallet's own devices only. A pairing grant can never
 *   include it, no matter what the user enables.
 * - `"shared"` — E2EE under the node's OWN keyring, reachable by a per-node
 *   pairing grant the user hands out (the website-pairing flow).
 * - `"public"` — world-readable plaintext. Nothing is `"public"` today.
 *
 * `user-accounts-auth` (exchange credentials) is intentionally absent: never a
 * configurable mirror-eligible option, at any layer.
 *
 * See `docs/content/client-sdk/website-pairing.md` for the access model.
 */
export type MirrorVisibility = 'private' | 'shared' | 'public'

export interface MirrorCollection {
  id: string
  defaultEnabled: boolean
  visibility: MirrorVisibility
}

export const MIRROR_COLLECTIONS: readonly MirrorCollection[] = [
  { id: 'user-accounts', defaultEnabled: true, visibility: 'shared' },
  { id: 'user-data', defaultEnabled: true, visibility: 'shared' },
  { id: 'user-strategies', defaultEnabled: true, visibility: 'shared' },
  { id: 'user-accounts-trading', defaultEnabled: false, visibility: 'shared' },
  { id: 'user-settings', defaultEnabled: false, visibility: 'private' },
] as const

export type MirrorCollectionId = (typeof MIRROR_COLLECTIONS)[number]['id']

export const DEFAULT_MIRROR_COLLECTIONS: MirrorCollectionId[] = MIRROR_COLLECTIONS
  .filter((c) => c.defaultEnabled)
  .map((c) => c.id)

export const THIRD_PARTY_ELIGIBLE_MIRROR_COLLECTIONS: MirrorCollectionId[] = MIRROR_COLLECTIONS
  .filter((c) => c.visibility !== 'private')
  .map((c) => c.id)

export function isKnownMirrorCollection(id: string): id is MirrorCollectionId {
  return MIRROR_COLLECTIONS.some((c) => c.id === id)
}

/** An UNKNOWN id resolves to `"private"` — the safe end of the enum, so a
 *  typo'd or stale id can never read as grant-reachable or world-readable. */
export function mirrorVisibilityFor(id: string): MirrorVisibility {
  return MIRROR_COLLECTIONS.find((c) => c.id === id)?.visibility ?? 'private'
}

/** DERIVED from `visibility`: "can a pairing grant ever reach this". */
export function isThirdPartyEligible(id: string): boolean {
  return mirrorVisibilityFor(id) !== 'private'
}

export function isPublicMirrorCollection(id: string): boolean {
  return mirrorVisibilityFor(id) === 'public'
}

/** Whether a collection's node is sealed under its own per-node keyring — the
 *  grantable ones. Drives both the writer's tier and the grant minting. */
export function isIsolatedMirrorCollection(id: string): boolean {
  return mirrorVisibilityFor(id) === 'shared'
}

/** `SpaceMirrorTier` as `starfish-replica/space` spells it: the storage axes a
 *  node is created under. `"shared"` maps to `"isolated"` rather than getting
 *  its own tier name — upstream names the access model, not our audience. */
export type MirrorStorageTier = 'private' | 'isolated' | 'public'

/**
 * Everything one `visibility` decides, as ONE table rather than ternaries
 * scattered across this module and the writer. Every row is a security
 * decision, so they are stated together where they can be tested against each
 * other.
 *
 * - `tier` — the storage axes handed to `createSpaceMirrorChannel`.
 * - `storage` — which content collection the node's document lives in:
 *   `docs` (`objdoc`, space-keyring E2EE), `invite` (`objinv`, per-node-keyring
 *   E2EE, cap-readable), `pub` (`objpub`, world-readable plaintext).
 * - `opaqueTitle` — whether the node's title must NOT name the collection,
 *   because Infra republishes a public node's title world-readable.
 */
export interface MirrorVisibilityRouting {
  tier: MirrorStorageTier
  storage: 'docs' | 'invite' | 'pub'
  opaqueTitle: boolean
}

export const MIRROR_ROUTING_BY_VISIBILITY: Readonly<
  Record<MirrorVisibility, MirrorVisibilityRouting>
> = {
  private: { tier: 'private', storage: 'docs', opaqueTitle: false },
  shared: { tier: 'isolated', storage: 'invite', opaqueTitle: false },
  public: { tier: 'public', storage: 'pub', opaqueTitle: true },
} as const

/**
 * ONE space per wallet, holding every mirrored collection whatever its
 * visibility. Found by name in the wallet's own space registry (`readSpaces()`)
 * — `starfish-spaces`' `Space` has no `meta`/`kind` field, so the name is the
 * marker; `createSpace` mints the id.
 *
 * This used to be three spaces, one per visibility, because a space keyring is
 * space-wide and a `space:member` grant reaches every enc node in the space —
 * so the only way to keep `user-settings` out of a website grant was to put it
 * in a different space. Per-node keyrings (`tier: "isolated"`) make that
 * unnecessary: a grant now reaches exactly one node. See
 * `docs/content/client-sdk/website-pairing.md`.
 */
export const MIRROR_SPACE_NAME = 'octobot-mirror'

/** Every routing decision for one collection, via its `visibility`. An unknown
 *  id inherits `mirrorVisibilityFor`'s safe `"private"` fallback. */
export function mirrorRoutingFor(collectionId: string): MirrorVisibilityRouting {
  return MIRROR_ROUTING_BY_VISIBILITY[mirrorVisibilityFor(collectionId)]
}

/** The `SpaceMirrorTier` a collection's node is created under. */
export function mirrorTierFor(collectionId: string): MirrorStorageTier {
  return mirrorRoutingFor(collectionId).tier
}

/**
 * The node's content path. The collection id comes FIRST because that is the
 * shape `starfish-replica/space` widened both `SpaceMirrorChannel.docPath` and
 * `readIsolatedSpaceMirror.docPath` to — one function literal shared by the writer and
 * the website-side reader, so a tier can never be written to one path and read
 * from another.
 *
 * `objinv` is the odd shape (`objects/n/{nodeId}/content`, not
 * `objects/{seg}/{nodeId}`) because it is per-node-scoped server-side: its
 * read roles are `space:member` OR `cap:read:objinv`, which is exactly what
 * lets a per-node grant holder fetch it without space membership. `objdoc`
 * has no cap fallback at all, which is why the isolated tier cannot use it.
 */
export function mirrorDocPath(collectionId: string, spaceId: string, nodeId: string): string {
  return mirrorDocPathForVisibility(mirrorVisibilityFor(collectionId), spaceId, nodeId)
}

/** The visibility-level primitive `mirrorDocPath` is a lookup in front of.
 *  Exported so the `"public"` branch is exercisable NOW — no collection has
 *  `visibility:"public"` yet, and the half that would leak is the one left
 *  unproven until someone flips a collection. */
export function mirrorDocPathForVisibility(
  visibility: MirrorVisibility,
  spaceId: string,
  nodeId: string,
): string {
  const { storage } = MIRROR_ROUTING_BY_VISIBILITY[visibility]
  return storage === 'invite'
    ? `spaces/${spaceId}/objects/n/${nodeId}/content`
    : `spaces/${spaceId}/objects/${storage}/${nodeId}`
}

export function mirrorDocPullPath(collectionId: string, spaceId: string, nodeId: string): string {
  return `/pull/${mirrorDocPath(collectionId, spaceId, nodeId)}`
}

export function mirrorDocPushPath(collectionId: string, spaceId: string, nodeId: string): string {
  return `/push/${mirrorDocPath(collectionId, spaceId, nodeId)}`
}

/**
 * The title a newly-created PUBLIC mirror node is given, in place of the
 * collection id `starfish-replica/space` would otherwise default to.
 *
 * `_project_objindex_public` republishes a public node's `title` into the
 * world-readable projection, so a descriptive one ("user-strategies") tells any
 * anonymous reader exactly what a wallet publishes. One constant shared by
 * every public collection carries zero bits about which collection a node
 * holds. Private and isolated titles live only in `objindex`, which is
 * `space:member` and unreachable by a per-node grant holder.
 */
export const MIRROR_PUBLIC_NODE_TITLE = 'public'

/** Title for a newly-created mirror node: opaque for public collections, the
 *  collection id (upstream's default) otherwise. */
export function mirrorNodeTitleFor(collectionId: string): string {
  return mirrorNodeTitleForVisibility(mirrorVisibilityFor(collectionId), collectionId)
}

/** The visibility-level primitive behind `mirrorNodeTitleFor`, exported for the
 *  same reason as `mirrorDocPathForVisibility`. */
export function mirrorNodeTitleForVisibility(
  visibility: MirrorVisibility,
  collectionId: string,
): string {
  return MIRROR_ROUTING_BY_VISIBILITY[visibility].opaqueTitle
    ? MIRROR_PUBLIC_NODE_TITLE
    : collectionId
}

/** `ObjectNode.type` for a mirror node is the collection id itself — one
 *  identifier space, nothing extra to keep in sync (see the module doc). */
export type MirrorNodeType = MirrorCollectionId
