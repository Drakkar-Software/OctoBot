import type { Session } from '@drakkar.software/starfish-spaces'
import { createSpaceMirrorChannel } from '@drakkar.software/starfish-replica/space'
import {
  mirrorDocPath,
  mirrorNodeTitleFor,
  mirrorTierFor,
  MIRROR_COLLECTIONS,
  MIRROR_SPACE_NAME,
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
  /** `null` when the space was never created (nothing has ever been enabled)
   *  — not an error, just "nothing to report". */
  spaceId: string | null
  created: MirrorCollectionId[]
  written: MirrorCollectionId[]
  cleared: MirrorCollectionId[]
}

/**
 * One full cloud-mirror sync cycle: find-or-create the wallet's mirror space,
 * plan what changed since last cycle, create any newly-enabled collections'
 * nodes, write every currently-enabled collection's projection, and clear any
 * collection the user just disabled.
 *
 * The space/node mechanics live in `starfish-replica/space`'s
 * `createSpaceMirrorChannel` — this is a thin adapter wiring the
 * `MIRROR_COLLECTIONS` registry and its tier routing into it.
 *
 * Callers (the node's writer, the mobile no-node writer) gate this behind the
 * `cloudSyncEnabled` setting themselves; this function assumes it was only
 * called because the setting is on.
 */
export async function syncCloudMirror(
  options: SyncCloudMirrorOptions,
): Promise<SyncCloudMirrorResult> {
  const { session, enabledCollectionIds, readSourceCollection } = options

  const channel = createSpaceMirrorChannel({
    name: 'octobot-cloud-mirror',
    session,
    // One space; `tier` is what separates the audiences within it. "shared"
    // -> "isolated" (own per-node keyring, so a grant reaches exactly that
    // node), "private" -> the space keyring, "public" -> world-readable
    // plaintext.
    collections: MIRROR_COLLECTIONS.map((c) => ({
      id: c.id,
      spaceName: MIRROR_SPACE_NAME,
      tier: mirrorTierFor(c.id),
    })),
    enabledIds: () => enabledCollectionIds,
    readSource: (id) => readSourceCollection(id),
    // Shared with the website-side reader so a tier is never written to one
    // path and read from another.
    docPath: mirrorDocPath,
    // Opaque for public nodes: their title is republished world-readable, so
    // it must not name the collection. See `mirrorNodeTitleFor`.
    title: mirrorNodeTitleFor,
  })
  // A direct app call, not a scheduler-driven one.
  await channel.sync({ callKind: 'classic' })

  const { spaces, created, written, cleared } = channel.result
  return {
    spaceId: spaces[MIRROR_SPACE_NAME] ?? null,
    created: created as MirrorCollectionId[],
    written: written as MirrorCollectionId[],
    cleared: cleared as MirrorCollectionId[],
  }
}
