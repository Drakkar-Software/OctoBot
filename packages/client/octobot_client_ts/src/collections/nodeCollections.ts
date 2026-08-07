/** The collections a self-hosted OctoBot node actually serves under
 *  `users/{identity}/...`. Each `encryptionInfo` is the HKDF `info` string the
 *  node derives its per-collection key from — it MUST equal
 *  `'octobot-sync-' + <node's own Collections enum value>`.
 *  @see packages/sync/octobot_sync/enums.py — Collections
 *  @see packages/sync/octobot_sync/crypto.py */
export type NodeCollectionInfo = {
  name: string
  storagePath: string
  encryptionInfo: string
  /** Node never accepts a push for this collection — pull only. */
  pullOnly?: boolean
  /** Append-only, push-only: each push publishes ONE queue element the node
   *  consumes and executes. Re-sending an element is re-executing it. */
  appendOnly?: boolean
}

export const NODE_COLLECTIONS = {
  /** Bundles the node-computed `automations`/`user_actions` fields alongside
   *  whatever else a higher-level client stores in the same document. */
  userData: {
    name: 'user-data',
    storagePath: 'users/{identity}/data',
    encryptionInfo: 'octobot-sync-user-data',
  },
  accounts: {
    name: 'accounts',
    storagePath: 'users/{identity}/accounts',
    encryptionInfo: 'octobot-sync-user-accounts',
  },
  /** The node stores this encrypted and opaque — it never reads a field. */
  settings: {
    name: 'settings',
    storagePath: 'users/{identity}/settings',
    encryptionInfo: 'octobot-sync-user-settings',
  },
  strategies: {
    name: 'strategies',
    storagePath: 'users/{identity}/strategies',
    encryptionInfo: 'octobot-sync-user-strategies',
  },
  actions: {
    name: 'actions',
    storagePath: 'users/{identity}/actions',
    encryptionInfo: 'octobot-sync-user-actions',
    appendOnly: true,
  },
  /** One document per exchange account — fan out over `{accountId}` yourself;
   *  there is no single "list all trading docs" pull. */
  accountTrading: {
    name: 'user-accounts-trading',
    storagePath: 'users/{identity}/accounts/{accountId}/trading',
    encryptionInfo: 'octobot-sync-user-accounts-trading',
    pullOnly: true,
  },
} as const satisfies Record<string, NodeCollectionInfo>

export type NodeCollectionKey = keyof typeof NODE_COLLECTIONS
