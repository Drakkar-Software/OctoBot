import type { Session } from '@drakkar.software/starfish-spaces'
import { createSpaceMirrorChannel } from '@drakkar.software/starfish-replica/space'
import {
  mirrorDocPath,
  mirrorNodeTitleFor,
  mirrorSpaceNameFor,
  mirrorTierFor,
  MIRROR_COLLECTIONS,
  MIRROR_SPACE_PRIVATE_NAME,
  MIRROR_SPACE_PUBLIC_NAME,
  MIRROR_SPACE_SHARED_NAME,
  type MirrorCollectionId,
} from './collections.js'

export interface SyncCloudMirrorOptions {
  session: Session
  /** Collection ids the user has currently enabled (`cloudSyncCollections`).
   *  Unknown ids are silently ignored — this function is not the place a
   *  malformed setting gets rejected, the settings layer already owns that. */
  enabledCollectionIds: readonly string[]
  /** Pull the CURRENT raw document for one enabled collection from its real
   *  source (the node, or a local store in the no-node case) — this
   *  function's caller owns how, `starfish-replica/space` owns only the
   *  CAS-write into the mirror space. Called once per collection being
   *  written, never for a collection being cleared. */
  readSourceCollection: (collectionId: MirrorCollectionId) => Promise<unknown>
}

export interface SyncCloudMirrorResult {
  /** `null` when that space was never created (nothing has ever been
   *  enabled for it) — not an error, just "nothing to report". */
  sharedSpaceId: string | null
  privateSpaceId: string | null
  publicSpaceId: string | null
  created: MirrorCollectionId[]
  written: MirrorCollectionId[]
  cleared: MirrorCollectionId[]
}

/**
 * One full cloud-mirror sync cycle across EVERY mirror space a collection
 * currently routes to (private / shared / public — see `collections.ts` for
 * why a visibility gets its own space): find-or-create
 * each space, plan what changed since last cycle, create any newly-enabled
 * collections' nodes, write every currently-enabled collection's projection
 * into its correct space, and clear any collection the user just disabled.
 * The actual space/node mechanics live in `@drakkar.software/starfish-replica/space`'s
 * `createSpaceMirrorChannel` — this function is a thin adapter wiring the
 * `MIRROR_COLLECTIONS` registry + `mirrorSpaceNameFor` routing policy into it.
 * Callers (the node's periodic writer, the mobile no-node writer) gate this
 * behind the `cloudSyncEnabled` setting themselves — this function does no
 * such gating on its own, it assumes it was only called because the setting
 * is on.
 */
export async function syncCloudMirror(
  options: SyncCloudMirrorOptions,
): Promise<SyncCloudMirrorResult> {
  const { session, enabledCollectionIds, readSourceCollection } = options

  const channel = createSpaceMirrorChannel({
    name: 'octobot-cloud-mirror',
    session,
    // `tier` is what turns a collection's `visibility` into real storage
    // axes: "public" -> `{access:"public", enc:false}` (world-readable
    // plaintext), everything else -> the channel default
    // `{access:"space", enc:true}`. `"shared"` is deliberately NOT its own
    // tier — a shared collection is still E2EE and member-gated, exactly like
    // a private one; what differs is only which SPACE it lands in, and
    // therefore whether a read-only grant can be minted over it.
    collections: MIRROR_COLLECTIONS.map((c) => ({
      id: c.id,
      spaceName: mirrorSpaceNameFor(c.id),
      tier: mirrorTierFor(c.id),
    })),
    enabledIds: () => enabledCollectionIds,
    readSource: (id) => readSourceCollection(id),
    // Routes public content to `objects/pub/` and everything else to
    // `objects/docs/`; shared with the website-side reader so a tier is never
    // written to one path and read from another.
    docPath: mirrorDocPath,
    // Opaque for public nodes: their title is republished world-readable, so
    // it must not name the collection. See `mirrorNodeTitleFor`.
    title: mirrorNodeTitleFor,
  })
  // A direct app call, not a scheduler-driven one — there is no periodic
  // ReplicaManager wired up to this yet (see the mobile no-node writer /
  // NothingToShareError just-in-time-sync doc comment at the call sites).
  await channel.sync({ callKind: 'classic' })

  const { spaces, created, written, cleared } = channel.result
  return {
    sharedSpaceId: spaces[MIRROR_SPACE_SHARED_NAME] ?? null,
    privateSpaceId: spaces[MIRROR_SPACE_PRIVATE_NAME] ?? null,
    publicSpaceId: spaces[MIRROR_SPACE_PUBLIC_NAME] ?? null,
    created: created as MirrorCollectionId[],
    written: written as MirrorCollectionId[],
    cleared: cleared as MirrorCollectionId[],
  }
}
