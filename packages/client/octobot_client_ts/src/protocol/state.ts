import type {
  AutomationState,
  WorkflowStatus,
  UserAction,
  AutomationActionResult,
  AccountActionResult,
  CreateAutomationConfiguration,
  CreateAccountConfiguration,
  EditAccountConfiguration,
  DeleteAccountConfiguration,
  RefreshAccountsConfiguration,
  CreateAccountAuthConfiguration,
  EditAccountAuthConfiguration,
  DeleteAccountAuthConfiguration,
  CreateExchangeConfigConfiguration,
  EditExchangeConfigConfiguration,
  DeleteExchangeConfigConfiguration,
  EditAutomationConfiguration,
  StopAutomationConfiguration,
  SignalAutomationConfiguration,
  Account as ProtocolAccount,
  ExchangeConfig,
  DetailedAsset,
  Strategy as ProtocolStrategy,
} from '@drakkar.software/octobot-protocol'
import { accountIdFromAuthId, accountIdFromExchangeConfigId } from './actions.js'
import type { StrategyKind } from './strategy/kinds.js'

/** A coarse run-status classification for `AutomationView` — never itself on
 *  the wire (the real wire enum is `AutomationState.status`'s `WorkflowStatus`,
 *  7 values); this is a client-side categorization, computed fresh by
 *  `workflowStatusToAutomationStatus` below, so it stays a local type here
 *  rather than living in the protocol package. */
export type AutomationRunStatus = 'live' | 'draft' | 'stopped'

// The node computes `users/{identity}/data` on every pull as a protocol
// UserDataState { automations: AutomationState[], user_actions: UserAction[] }
// (snake_case pydantic JSON). This is bidirectional wire state — parse it
// READ-TIME with the tolerant functions below; a caller with its own local
// mirror (tombstones, CRDT merge) reconciles the two itself, one layer up.

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

// Every parser below is cached per input document reference: a caller reading
// through `useSyncExternalStore`-style selectors needs a stable reference for
// the same input, or a fresh .filter()/.map() per call trips React's
// "getSnapshot should be cached" infinite-loop guard. A store write replaces
// the data object, so a new reference recomputes. Exported (not just used
// internally) so a caller building its own local-merge layer on top of these
// parsers — see docs/10-advanced-primitives.md — can give its own derived
// values the same reference-stability guarantee instead of reimplementing it.
export function cachedByDoc<T>(compute: (doc: Record<string, unknown>) => T, empty: T) {
  const cache = new WeakMap<object, T>()
  return (doc: unknown): T => {
    if (!isRecord(doc)) return empty
    const hit = cache.get(doc)
    if (hit !== undefined) return hit
    const out = compute(doc)
    cache.set(doc, out)
    return out
  }
}

/** Derives a `StrategyKind` from a protocol Strategy's configuration —
 *  for callers reconstructing a strategy from raw node data that need to tag
 *  it with the same kind derivation a local persisted doc would carry. */
export function protocolStrategyKind(configuration: ProtocolStrategy['configuration']): StrategyKind {
  switch (configuration.configuration_type) {
    case 'market_making':    return 'mm'
    case 'copy':             return 'copy'
    case 'generic_process':  return 'custom'
    case 'generic_workflow': return 'ai-agents'
    case 'trading_tentacles': {
      const name = (configuration as { name?: string }).name
      if (name === 'GridTradingMode')  return 'grid'
      if (name === 'DCATradingMode')   return 'dca'
      if (name === 'IndexTradingMode') return 'basket'
      return 'custom'
    }
    default: return 'custom'
  }
}

const EMPTY_AUTOMATION_STATES: AutomationState[] = []
const EMPTY_USER_ACTIONS: UserAction[] = []

/** Node-reported automation states from a pulled user-data document. Excludes
 *  any entry carrying a `kind` field — that marks a caller's own local
 *  mirror unioned into the same array, not node state. */
export const parseNodeAutomationStates: (doc: unknown) => AutomationState[] = cachedByDoc(
  (doc) => {
    if (!Array.isArray(doc.automations)) return EMPTY_AUTOMATION_STATES
    return doc.automations.filter(
      (entry): entry is AutomationState =>
        isRecord(entry) && typeof entry.id === 'string' && !('kind' in entry),
    )
  },
  EMPTY_AUTOMATION_STATES,
)

/** Node-reported user actions (with execution status + result) from a pulled
 *  user-data document. Pulling the append-only `actions` collection itself
 *  always returns empty — the node reports execution state through
 *  user-data, not through the queue collection. */
export const parseNodeUserActions: (doc: unknown) => UserAction[] = cachedByDoc(
  (doc) => {
    if (!Array.isArray(doc.user_actions)) return EMPTY_USER_ACTIONS
    return doc.user_actions.filter(
      (entry): entry is UserAction => isRecord(entry) && typeof entry.id === 'string',
    )
  },
  EMPTY_USER_ACTIONS,
)

/** Protocol workflow status → a coarse live/draft/stopped classification.
 *  'canceled', 'failed', 'completed' and any future unknown value map to
 *  'stopped' so a non-running workflow never renders as a live bot. */
export function workflowStatusToAutomationStatus(status: WorkflowStatus | string | undefined): AutomationRunStatus {
  switch (status) {
    case 'scheduled':
    case 'periodic':
    case 'running':
      return 'live'
    case 'pending':
      return 'draft'
    default:
      return 'stopped'
  }
}

/** Node-reported failure for an automation: error_message is the protocol
 *  enum-ish summary, error the detailed string. */
export function automationErrorOf(state: AutomationState): string | null {
  return state.error_message ?? state.error ?? null
}

/** Normalize a raw node `assets` value (either flat `DetailedAsset[]` or
 *  nested `DetailedAssetsForTradingType[]`) into a flat `DetailedAsset[]`.
 *  The 0.4.0 schema declares the nested shape but the node serializes flat
 *  items (bypasses pydantic validation when filling) — accept both. */
export function normalizeNodeAssets(raw: unknown): DetailedAsset[] {
  if (!Array.isArray(raw)) return []
  const out: DetailedAsset[] = []
  for (const entry of raw) {
    if (!isRecord(entry)) continue
    if (typeof entry.symbol === 'string') {
      out.push(entry as unknown as DetailedAsset)
    } else if (Array.isArray(entry.assets)) {
      for (const nested of entry.assets) {
        if (isRecord(nested) && typeof nested.symbol === 'string') out.push(nested as unknown as DetailedAsset)
      }
    }
  }
  return out
}

/** Holdings from an AutomationState, normalized. */
export function automationHoldings(state: AutomationState): DetailedAsset[] {
  return normalizeNodeAssets(state.assets as unknown)
}

// The accounts collection is node-owned and pull-only: a client push is
// dead-lettered into opaque storage and every pull returns the node's
// AccountsState { accounts, exchange_configs }.

const EMPTY_NODE_ACCOUNTS: ProtocolAccount[] = []
const EMPTY_EXCHANGE_CONFIGS: ExchangeConfig[] = []

export const parseNodeAccounts: (doc: unknown) => ProtocolAccount[] = cachedByDoc(
  (doc) => {
    if (!Array.isArray(doc.accounts)) return EMPTY_NODE_ACCOUNTS
    return doc.accounts.filter(
      (entry): entry is ProtocolAccount => isRecord(entry) && typeof entry.id === 'string',
    )
  },
  EMPTY_NODE_ACCOUNTS,
)

export const parseNodeExchangeConfigs: (doc: unknown) => ExchangeConfig[] = cachedByDoc(
  (doc) => {
    if (!Array.isArray(doc.exchange_configs)) return EMPTY_EXCHANGE_CONFIGS
    return doc.exchange_configs.filter(
      (entry): entry is ExchangeConfig => isRecord(entry) && typeof entry.id === 'string',
    )
  },
  EMPTY_EXCHANGE_CONFIGS,
)

/** Node-reported asset quantities for an account, flattened. Kept as its own
 *  named function (rather than inlining `normalizeNodeAssets(na.assets)`
 *  at call sites) so `accountViewOf`'s intent reads clearly. */
export function accountHoldingsFromNodeState(na: ProtocolAccount): DetailedAsset[] {
  return normalizeNodeAssets(na.assets as unknown)
}

// ── Typed user-action accessors ──────────────────────────────────────────────
// Discriminated reads over UserAction.result / .configuration — replace
// ad-hoc `as X` casts.

export function automationResultOf(action: UserAction): AutomationActionResult | null {
  return action.result?.result_type === 'automation' ? (action.result as AutomationActionResult) : null
}

export function accountResultOf(action: UserAction): AccountActionResult | null {
  return action.result?.result_type === 'account' ? (action.result as AccountActionResult) : null
}

export function actionErrorDetails(action: UserAction): string | null {
  // Every 0.4.0 result variant (automation, account, account_auth,
  // exchange_config, strategy) carries the same optional error_details slot
  // plus a structured error_message enum (e.g. 'strategy_not_found'). Both
  // are optional — fall back to the enum so a failure is never blank.
  const result = action.result as { error_details?: string; error_message?: string } | undefined
  return result?.error_details ?? result?.error_message ?? null
}

/** The automation id a completed automation_create produced. */
export function createdAutomationIdOf(action: UserAction): string | null {
  return automationResultOf(action)?.created_automation_id ?? null
}

/** The account id an `account_create` carries. Unlike automations, account
 *  ids are client-assigned and reused verbatim by the node, so the creating
 *  action alone identifies the account it will produce. */
export function createdAccountIdOf(action: UserAction): string | null {
  const cfg = action.configuration
  if (cfg?.action_type !== 'account_create') return null
  return (cfg as CreateAccountConfiguration).configuration?.id ?? null
}

/** Which domain a user action belongs to, purely from its wire `action_type`. */
export type UserActionDomain = 'accounts' | 'automations'

const ACTION_TYPE_DOMAIN: Record<string, UserActionDomain> = {
  account_create: 'accounts',
  account_edit: 'accounts',
  account_delete: 'accounts',
  account_auth_create: 'accounts',
  account_auth_edit: 'accounts',
  account_auth_delete: 'accounts',
  exchange_config_create: 'accounts',
  exchange_config_edit: 'accounts',
  exchange_config_delete: 'accounts',
  accounts_refresh: 'accounts',
  automation_create: 'automations',
  automation_edit: 'automations',
  automation_stop: 'automations',
  automation_signal: 'automations',
  // A strategy only exists to back an automation — same domain.
  strategy_create: 'automations',
  strategy_edit: 'automations',
  strategy_delete: 'automations',
}

/** Null for action types with no owning domain (a future protocol action
 *  added here before its domain is wired in degrades to "belongs nowhere"
 *  rather than crashing a domain filter). */
export function actionDomainOf(action: UserAction): UserActionDomain | null {
  const type = action.configuration?.action_type
  return type ? ACTION_TYPE_DOMAIN[type] ?? null : null
}

/** The automation an action targets — explicit id for edit/stop/signal, the
 *  node-reported created id for create. */
export function targetAutomationIdOf(action: UserAction): string | null {
  const cfg = action.configuration
  if (!cfg) return null
  switch (cfg.action_type) {
    case 'automation_edit': return (cfg as EditAutomationConfiguration).id
    case 'automation_stop': return (cfg as StopAutomationConfiguration).id
    case 'automation_signal': return (cfg as SignalAutomationConfiguration).automation_id
    case 'automation_create': return createdAutomationIdOf(action)
    default: return null
  }
}

/** Every account id an action targets. `account_create`/`_edit`/`_delete`
 *  carry the account id directly; `account_auth_*`/`exchange_config_*` carry
 *  an `auth_*`/`cfg_*` id derived from it and are reversed back to the
 *  account id. `accounts_refresh` with no explicit `account_ids` targets
 *  every account — callers should treat that case as "matches any account"
 *  rather than reading an empty array from here. */
export function targetAccountIdsOf(action: UserAction): string[] {
  const cfg = action.configuration
  if (!cfg) return []
  switch (cfg.action_type) {
    case 'account_create': {
      const id = createdAccountIdOf(action)
      return id ? [id] : []
    }
    case 'account_edit': return [(cfg as EditAccountConfiguration).id]
    case 'account_delete': return [(cfg as DeleteAccountConfiguration).id]
    case 'accounts_refresh': return (cfg as RefreshAccountsConfiguration).account_ids ?? []
    case 'account_auth_create':
      return [accountIdFromAuthId((cfg as CreateAccountAuthConfiguration).configuration.id)]
    case 'account_auth_edit': return [accountIdFromAuthId((cfg as EditAccountAuthConfiguration).id)]
    case 'account_auth_delete': return [accountIdFromAuthId((cfg as DeleteAccountAuthConfiguration).id)]
    case 'exchange_config_create':
      return [accountIdFromExchangeConfigId((cfg as CreateExchangeConfigConfiguration).configuration.id)]
    case 'exchange_config_edit':
      return [accountIdFromExchangeConfigId((cfg as EditExchangeConfigConfiguration).id)]
    case 'exchange_config_delete':
      return [accountIdFromExchangeConfigId((cfg as DeleteExchangeConfigConfiguration).id)]
    default: return []
  }
}

/** Whether a queued action targets the given account — an `accounts_refresh`
 *  with no explicit `account_ids` refreshes every account, so it counts as
 *  targeting all of them. */
export function actionTargetsAccount(action: UserAction, accountId: string): boolean {
  const cfg = action.configuration
  if (cfg?.action_type === 'accounts_refresh' && !(cfg as RefreshAccountsConfiguration).account_ids) return true
  return targetAccountIdsOf(action).includes(accountId)
}

/** Pull the (automationId, strategy ref) an `automation_edit`/`automation_create`
 *  action carries, if any — the shared per-action extraction both
 *  `automationStrategyRefsOf` and `automationStrategyRefOf` scan for, each
 *  aggregating it differently (see their own doc comments). */
function automationStrategyRefFromAction(
  action: UserAction,
): { automationId: string; ref: { id: string; version?: string } } | null {
  const cfg = action.configuration
  if (!cfg) return null
  let automationId: string | undefined
  let ref: { id: string; version: string } | undefined
  if (cfg.action_type === 'automation_edit') {
    automationId = (cfg as EditAutomationConfiguration).id
    ref = (cfg as EditAutomationConfiguration).configuration?.strategy
  } else if (cfg.action_type === 'automation_create') {
    automationId = createdAutomationIdOf(action) ?? undefined
    ref = (cfg as CreateAutomationConfiguration).configuration?.strategy
  }
  if (!automationId || !ref?.id) return null
  return { automationId, ref: { id: ref.id, version: ref.version } }
}

/** The strategy (id, version) every automation referenced in `actions` runs,
 *  recovered from the action history in one pass: node AutomationStates
 *  carry no strategy reference — the automation_create / automation_edit
 *  configurations are the only wire record. The newest action targeting an
 *  automation wins (an edit supersedes the create). Prefer this over calling
 *  `automationStrategyRefOf` once per automation against the same `actions`
 *  array — that repeats the full scan per automation (O(automations ×
 *  actions)); this does the equivalent work once (O(actions)). */
export function automationStrategyRefsOf(actions: UserAction[]): Map<string, { id: string; version?: string }> {
  const best = new Map<string, { id: string; version?: string }>()
  const bestAt = new Map<string, string>()
  for (const action of actions) {
    const found = automationStrategyRefFromAction(action)
    if (!found) continue
    const at = action.updated_at ?? action.created_at ?? ''
    const prevAt = bestAt.get(found.automationId)
    if (prevAt === undefined || at >= prevAt) {
      best.set(found.automationId, found.ref)
      bestAt.set(found.automationId, at)
    }
  }
  return best
}

/** The strategy (id, version) one automation runs, scanning `actions` once
 *  for just that id — a deliberately separate, targeted pass rather than
 *  `automationStrategyRefsOf(actions).get(automationId)`, so a single lookup
 *  doesn't pay for building a map entry for every OTHER automation in the
 *  action history too. Resolving more than one automation against the same
 *  `actions` array should call `automationStrategyRefsOf` once instead — this
 *  rescans on every call, which is fine for one-off lookups but O(automations
 *  × actions) in a loop. */
export function automationStrategyRefOf(
  actions: UserAction[],
  automationId: string,
): { id: string; version?: string } | null {
  let best: { id: string; version?: string } | undefined
  let bestAt: string | undefined
  for (const action of actions) {
    const found = automationStrategyRefFromAction(action)
    if (!found || found.automationId !== automationId) continue
    const at = action.updated_at ?? action.created_at ?? ''
    if (bestAt === undefined || at >= bestAt) {
      best = found.ref
      bestAt = at
    }
  }
  return best ?? null
}

/** Human-facing name carried by the action's configuration, when one exists.
 *  Returns null when the configuration only carries an opaque id (stop /
 *  delete actions) — callers fall back to their own type label. */
export function actionDisplayName(action: UserAction): string | null {
  const cfg = action.configuration
  if (!cfg) return null
  switch (cfg.action_type) {
    case 'automation_create': return (cfg as CreateAutomationConfiguration).configuration?.name ?? null
    case 'automation_edit':   return (cfg as EditAutomationConfiguration).configuration?.name ?? null
    case 'account_create':
    case 'account_edit':
    // Strategy actions carry the strategy's display name — the likeliest
    // failure in the inbox (a strategy race) should not title generically.
    case 'strategy_create':
    case 'strategy_edit': {
      const config = (cfg as { configuration?: { name?: string } }).configuration
      return config?.name ?? null
    }
    default: return null
  }
}
