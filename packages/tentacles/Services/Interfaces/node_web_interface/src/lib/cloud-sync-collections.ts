/**
 * Node collections the space-mirror can offer, mirroring the backend's
 * `DEFAULT_CLOUD_SYNC_COLLECTIONS` / `CLOUD_SYNC_FORBIDDEN_COLLECTION`
 * (`octobot_services/constants.py`) and mobile2's own copy of this same
 * table (`frontend/mobile2/src/lib/settings/cloudSyncCollections.ts`).
 *
 * `thirdPartyEligible: false` means a read-only pairing grant can never
 * include the collection, no matter what the user enables here — used to
 * render the eligibility badge in the "Configure" modal. `user-accounts-auth`
 * (exchange credentials) is intentionally absent from this list: it is never
 * offered as a configurable option, at any layer, on any platform.
 */
export interface MirrorCollection {
  id: string
  label: string
  description: string
  defaultEnabled: boolean
  thirdPartyEligible: boolean
}

export const MIRROR_COLLECTIONS: readonly MirrorCollection[] = [
  {
    id: "user-accounts",
    label: "Accounts",
    description: "Portfolio holdings — balances, connected/simulated status.",
    defaultEnabled: true,
    thirdPartyEligible: true,
  },
  {
    id: "user-data",
    label: "Automations",
    description: "Automation configuration and status.",
    // Off by default: the node has no local reader for this collection yet
    // (octobot_sync.mirror.node_collections raises NotImplementedError) — the
    // backend's DEFAULT_CLOUD_SYNC_COLLECTIONS excludes it for the same reason.
    // Still selectable (a future reader can turn this back on), just not pre-checked.
    defaultEnabled: false,
    thirdPartyEligible: true,
  },
  {
    id: "user-strategies",
    label: "Strategies",
    description: "Strategy identities used by your automations.",
    defaultEnabled: true,
    thirdPartyEligible: true,
  },
  {
    id: "user-accounts-trading",
    label: "Trade history",
    description: "Orders, trades, and positions — larger data, off by default.",
    defaultEnabled: false,
    thirdPartyEligible: true,
  },
  {
    id: "user-settings",
    label: "Settings",
    description:
      "Node configuration. Useful for syncing your own devices — never shared with a paired third-party site, even when enabled.",
    defaultEnabled: false,
    thirdPartyEligible: false,
  },
] as const

export const DEFAULT_CLOUD_SYNC_COLLECTIONS: string[] = MIRROR_COLLECTIONS
  .filter((c) => c.defaultEnabled)
  .map((c) => c.id)

/** Pure toggle transform for the "Configure" modal's per-row checkbox. */
export function nextCollectionsOnToggle(
  current: readonly string[],
  id: string,
  on: boolean,
): string[] {
  if (on) return current.includes(id) ? [...current] : [...current, id]
  return current.filter((c) => c !== id)
}
