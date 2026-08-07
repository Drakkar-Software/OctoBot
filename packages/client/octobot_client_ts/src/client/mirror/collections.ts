/**
 * Node collections the space-mirror can offer — the canonical definition
 * this whole feature's per-platform copies (mobile2's `cloudSyncCollections.ts`,
 * the node web UI's `cloud-sync-collections.ts`) are meant to eventually source
 * from instead of duplicating. Ids are the SAME wire collection names the node's
 * own sync layer already uses (`wire-contract.md`'s `Collections` enum values) —
 * one identifier space across the writer (this package, and the node's Python
 * writer), the settings UI, and the read-only grant, not three.
 *
 * `visibility` is who can ever reach a collection's mirrored copy, as one
 * closed three-value enum rather than a pile of independent booleans:
 *
 * - `"private"` — the wallet's own devices only. A read-only pairing grant can
 *   never include it, no matter what the user enables. `user-settings` is
 *   mirror-eligible (useful for syncing a wallet's own devices) but never
 *   offered to a paired third party.
 * - `"shared"` — still E2EE and member-gated, but reachable by a read-only
 *   pairing grant the user hands out (the website-pairing flow).
 * - `"public"` — world-readable plaintext at its storage URL. Nothing is
 *   `"public"` today; the value exists so a future explicitly-published
 *   collection has somewhere to land, with the storage/space routing below
 *   already correct for it.
 *
 * `isThirdPartyEligible` is DERIVED from this (`visibility !== "private"`), so
 * callers that only care about the "can a grant reach it" axis are unaffected
 * by the split.
 *
 * `user-accounts-auth` (exchange credentials) is intentionally absent from this
 * list entirely: never a configurable mirror-eligible option, at any layer.
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

/** An UNKNOWN id resolves to `"private"` — the safe end of the enum. Every
 *  derived helper below inherits that, so a typo'd or stale collection id can
 *  never accidentally read as grant-reachable or world-readable. */
export function mirrorVisibilityFor(id: string): MirrorVisibility {
  return MIRROR_COLLECTIONS.find((c) => c.id === id)?.visibility ?? 'private'
}

/** DERIVED from `visibility`, not a stored field: "can a read-only pairing
 *  grant ever reach this collection". Both non-private tiers qualify. */
export function isThirdPartyEligible(id: string): boolean {
  return mirrorVisibilityFor(id) !== 'private'
}

export function isPublicMirrorCollection(id: string): boolean {
  return mirrorVisibilityFor(id) === 'public'
}

/**
 * `SpaceMirrorTier` as `starfish-replica/space` spells it: the storage axes a
 * node is created under. `"public"` -> `{access:"public", enc:false}`,
 * `"private"` -> the channel default `{access:"space", enc:true}`. Only two
 * values, deliberately: `"shared"` is NOT its own tier, because a shared
 * collection is stored exactly like a private one (E2EE, member-gated) — what
 * differs is only which SPACE it lands in, and therefore whether a read-only
 * grant can be minted over it.
 */
export type MirrorStorageTier = 'private' | 'public'

/**
 * Everything one `visibility` decides, as ONE table rather than four
 * independent ternaries scattered across this module and the writer. Every row
 * is a security decision, so they are stated together where they can be read
 * (and tested) against each other:
 *
 * - `spaceName` — which of the three dedicated mirror spaces the node lives in
 *   (see `MIRROR_SPACE_*` below for why one space per visibility).
 * - `tier` — the storage axes handed to `createSpaceMirrorChannel`.
 * - `storage` — the storage collection segment of the node's content path:
 *   `docs` (`objdoc`) for the private merge-doc, `pub` (`objpub`) for the
 *   world-readable plaintext one.
 * - `opaqueTitle` — whether the node's title must NOT name the collection,
 *   because Infra republishes a public node's title world-readable (see
 *   `MIRROR_PUBLIC_NODE_TITLE`).
 */
export interface MirrorVisibilityRouting {
  spaceName: string
  tier: MirrorStorageTier
  storage: 'docs' | 'pub'
  opaqueTitle: boolean
}

/**
 * Where one collection's node content is stored, keyed off its `visibility`.
 * The collection id comes FIRST because that is the shape
 * `starfish-replica/space` widened both `SpaceMirrorChannel.docPath` and
 * `readSpaceMirror.docPath` to — one function literal shared by the writer and
 * the website-side reader, so a tier can never be written to one path and
 * read from another.
 *
 * - private/shared -> `objdoc` (`objects/docs/`), the generic private
 *   merge-doc: the canonical content location for a node created
 *   `access:"space", enc:true`, which is exactly how the writer creates them.
 *   Same routing rule OctoBot strategy graphs and OctoVault page content
 *   already follow, so a generic DKSpaces client finds the content where it
 *   expects to.
 * - public -> `objpub` (`objects/pub/`), the plaintext world-readable
 *   counterpart, matching Infra's `dk_spaces` collection definition (and this
 *   repo's Python-side routing, `octobot_sync/mirror/collections.py`). A
 *   `tier:"public"` node is stored
 *   `access:"public", enc:false`; writing it to `objdoc` would put
 *   world-readable content on the private merge-doc path.
 *
 * There was briefly a dedicated `mirrordoc` collection here, purely because
 * `objdoc` was capped at 256 KiB and a raw `user-accounts-trading` projection
 * does not fit (a measured one is 146,530 B plaintext, and delegated sealing
 * adds base64's 4/3). `objdoc` is now 10 MiB and `mirrordoc` is gone — it was
 * a byte-for-byte clone differing only in that integer, and it put node
 * content off the canonical path.
 *
 * No collision with ordinary user documents, on two independent grounds: the
 * mirror uses its own dedicated spaces (`MIRROR_SPACE_SHARED_NAME` /
 * `_PRIVATE_NAME` / `_PUBLIC_NAME`, below), and node ids are minted by
 * `createNode` rather than derived from a collection id.
 */
export function mirrorDocPath(collectionId: string, spaceId: string, nodeId: string): string {
  return mirrorDocPathForVisibility(mirrorVisibilityFor(collectionId), spaceId, nodeId)
}

/** The visibility-level primitive `mirrorDocPath` is a lookup in front of.
 *  Exported so the `"public"` branch is exercisable NOW — no collection has
 *  `visibility:"public"` yet, so routing it through a collection id could only
 *  ever test the private/shared half, and the half that would leak is the one
 *  left unproven until the day someone flips a collection. */
export function mirrorDocPathForVisibility(
  visibility: MirrorVisibility,
  spaceId: string,
  nodeId: string,
): string {
  return `spaces/${spaceId}/objects/${MIRROR_ROUTING_BY_VISIBILITY[visibility].storage}/${nodeId}`
}

export function mirrorDocPullPath(collectionId: string, spaceId: string, nodeId: string): string {
  return `/pull/${mirrorDocPath(collectionId, spaceId, nodeId)}`
}

export function mirrorDocPushPath(collectionId: string, spaceId: string, nodeId: string): string {
  return `/push/${mirrorDocPath(collectionId, spaceId, nodeId)}`
}

/**
 * Well-known names for the wallet's three dedicated mirror spaces, used to
 * find them in the wallet's own space registry (`readSpaces()`) without
 * depending on a fixed id — `starfish-spaces`' `Space` type has no separate
 * `meta`/`kind` field to mark it with, so the name itself is the marker.
 * `createSpace` assigns a fresh generated id regardless; these names are
 * what `findOrCreate` matches on.
 *
 * ONE SPACE PER VISIBILITY, not one space total — load-bearing, not cosmetic,
 * and for two independent reasons.
 *
 * private vs shared. A read-only pairing grant is minted via
 * `inviteToNode(..., {isolated: false})` (see the Python-parity finding:
 * isolated per-node keyrings aren't available, so the grant is a
 * `space:member`-shaped cap). A space-member cap's `spaceMemberScope` covers
 * `spaces/{spaceId}/**` — i.e. EVERY enc node in that space, not just the one
 * the pairing UI shows the user. If `user-settings` (`visibility:"private"`)
 * shared a space with `user-accounts`/`user-data`/etc, ANY read-only grant
 * into that space would silently also decrypt settings — the exact leak
 * `visibility:"private"` is supposed to prevent. Separate spaces make that
 * leak structurally impossible instead of merely discouraged: a grant minted
 * against the SHARED space can never reach anything in the PRIVATE space,
 * because they are different spaces with different keyrings and different
 * `_access` docs entirely.
 *
 * shared vs public. Infra's `_project_objindex_public` lifts every node whose
 * STORED access is `"public"` out of a space's object index and upserts
 * `{id, title, type, updatedAt}` into the world-readable `_index/objects/public`
 * projection — KEYED BY spaceId. So publishing a node discloses the id of the
 * space holding it, to anonymous callers. That is the same id a read-only
 * grant holder is handed. A public node parked in the SHARED space would
 * therefore hand every anonymous reader the shared space's id, turning a
 * space whose contents are only supposed to be reachable with a grant into one
 * whose existence and node inventory anyone can enumerate. A third space keeps
 * the published id disjoint from the granted one.
 */
export const MIRROR_SPACE_SHARED_NAME = 'octobot-mirror'
export const MIRROR_SPACE_PRIVATE_NAME = 'octobot-mirror-private'
export const MIRROR_SPACE_PUBLIC_NAME = 'octobot-mirror-public'

/** The one routing table (see `MirrorVisibilityRouting`). `"shared"` differs
 *  from `"private"` ONLY in its space — same tier, same storage path, same
 *  descriptive title — which is the whole point: a shared collection is stored
 *  identically to a private one, it just lives somewhere a read-only grant can
 *  be minted against. */
export const MIRROR_ROUTING_BY_VISIBILITY: Readonly<
  Record<MirrorVisibility, MirrorVisibilityRouting>
> = {
  private: {
    spaceName: MIRROR_SPACE_PRIVATE_NAME,
    tier: 'private',
    storage: 'docs',
    opaqueTitle: false,
  },
  shared: {
    spaceName: MIRROR_SPACE_SHARED_NAME,
    tier: 'private',
    storage: 'docs',
    opaqueTitle: false,
  },
  public: {
    spaceName: MIRROR_SPACE_PUBLIC_NAME,
    tier: 'public',
    storage: 'pub',
    opaqueTitle: true,
  },
} as const

/** Every routing decision for one collection, via its `visibility`. An unknown
 *  id inherits `mirrorVisibilityFor`'s safe `"private"` fallback. */
export function mirrorRoutingFor(collectionId: string): MirrorVisibilityRouting {
  return MIRROR_ROUTING_BY_VISIBILITY[mirrorVisibilityFor(collectionId)]
}

/** Which of the three mirror spaces a collection's node lives in. */
export function mirrorSpaceNameFor(collectionId: string): string {
  return mirrorRoutingFor(collectionId).spaceName
}

/** The `SpaceMirrorTier` a collection's node is created under — what the writer
 *  hands `createSpaceMirrorChannel`. */
export function mirrorTierFor(collectionId: string): MirrorStorageTier {
  return mirrorRoutingFor(collectionId).tier
}

/**
 * The title a newly-created PUBLIC mirror node is given, in place of the
 * collection id `starfish-replica/space` would otherwise default to.
 *
 * Same disclosure as the space split above: `_project_objindex_public`
 * republishes a public node's `title` into the world-readable projection, so
 * a descriptive one ("user-strategies") tells any anonymous reader exactly
 * what a given wallet publishes. One constant shared by every public
 * collection carries zero bits about which collection a node holds.
 *
 * NOTE: the node's own id would be the ideal opaque title, but it does not
 * exist yet at the point the title is chosen — `starfish-spaces`' `createNode`
 * mints it (`nodeIdPrefix` + random) from the input this title is part of, and
 * upstream's hook is `title(collectionId)`, with no node id to hand it. A
 * fixed constant is the closest achievable equivalent; giving public nodes a
 * genuine node-id title would need an upstream post-create title patch.
 */
export const MIRROR_PUBLIC_NODE_TITLE = 'public'

/** Title for a newly-created mirror node: opaque for public collections,
 *  the collection id (upstream's default) for private/shared ones. */
export function mirrorNodeTitleFor(collectionId: string): string {
  return mirrorNodeTitleForVisibility(mirrorVisibilityFor(collectionId), collectionId)
}

/** The visibility-level primitive behind `mirrorNodeTitleFor`, exported for the
 *  same reason as `mirrorDocPathForVisibility`: the opaque-title branch is the
 *  one that leaks if it regresses, and it is unreachable through a collection
 *  id until a collection is actually published. */
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
