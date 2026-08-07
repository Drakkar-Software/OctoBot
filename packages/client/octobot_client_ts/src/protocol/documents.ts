import type {
  AutomationState,
  UserAction,
  AccountTradingWithAccountId,
} from '@drakkar.software/octobot-protocol'

/** What the node computes at `users/{identity}/data` on every pull. A caller
 *  with its own local document that stores additional fields in the same
 *  blob (a dashboard cache, say) should intersect its own type with this
 *  one rather than redeclaring `automations`/`user_actions`. */
export type UserDataState = {
  automations: AutomationState[]
  user_actions: UserAction[]
}

/** What the node returns at `users/{identity}/accounts` — pull-only, the
 *  node never accepts a push for this document. */
export type AccountsState = {
  accounts?: unknown[]
  exchange_configs?: unknown[]
}

/** `users/{identity}/actions` — append-only, push-only. Wire elements only;
 *  a caller's own local queue mirror is a different, larger shape. */
export type UserActionsDocument = {
  version?: string
  items: UserAction[]
}

/** `users/{identity}/accounts/{accountId}/trading` — one document per
 *  account; there is no single "list every account's trading doc" pull. */
export type AccountTradingDocument = AccountTradingWithAccountId
