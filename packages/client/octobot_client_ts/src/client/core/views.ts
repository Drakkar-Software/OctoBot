import type {
  Account as ProtocolAccount,
  AccountSpecifics,
  ExchangeConfig,
  AutomationState,
  DetailedAsset,
  UserAction,
} from '@drakkar.software/octobot-protocol'
import type { AutomationRunStatus } from '../../protocol/state.js'
import {
  accountHoldingsFromNodeState,
  workflowStatusToAutomationStatus,
  automationErrorOf,
  automationHoldings,
  automationStrategyRefOf,
  automationStrategyRefsOf,
} from '../../protocol/state.js'

// AccountView/AutomationView/AccountKind are client-computed projections, not
// wire types — neither is ever itself serialized, each is rebuilt fresh by
// accountViewOf/automationViewOf from a real wire record (Account /
// AutomationState). They are hand-declared here rather than generated from
// the OpenAPI spec for exactly that reason.

/** Coarse account category for `AccountView.type`. Collapses broker/bank/
 *  asset accounts under 'generic': those kinds only exist client-side
 *  (Astrolab's mirror), the node models them as generic. */
export type AccountKind = 'exchange' | 'wallet' | 'generic'

/** An `Account` projected for client use: node-owned fields plus the
 *  exchange resolved through `exchange_configs`, and holdings normalized to
 *  a flat `DetailedAsset[]`. */
export type AccountView = ProtocolAccount & {
  name: string
  type: AccountKind
  exchange?: string
  simulated: boolean
  connected: boolean
  holdings: DetailedAsset[]
  raw: ProtocolAccount
}

/** An `AutomationState` projected for client use: run status collapsed to
 *  three values, the strategy it was created from (recovered from action
 *  history — `AutomationState` itself carries no strategy reference), and
 *  holdings normalized to a flat `DetailedAsset[]`. */
export type AutomationView = Omit<AutomationState, 'status' | 'error'> & {
  name: string
  status: AutomationRunStatus
  accountIds: string[]
  strategy: { id: string; version?: string } | null
  error: string | null
  holdings: DetailedAsset[]
  raw: AutomationState
}

/** The `exchange_config_ids` a specifics variant carries, if any. Only
 *  exchange, blockchain and broker accounts can name one; generic, bank and
 *  asset accounts cannot resolve an exchange at all. Exported so a caller
 *  building its own account view on top of `AccountSpecifics` (as
 *  `octobot-sdk`'s `accountFromNodeState` does) doesn't have to re-derive
 *  this rule itself. */
export function exchangeConfigIdOf(specifics: AccountSpecifics | undefined): string | undefined {
  if (!specifics) return undefined
  if (specifics.account_type === 'exchange') return specifics.exchange_config_ids[0]
  if (specifics.account_type === 'blockchain' || specifics.account_type === 'broker') {
    return specifics.exchange_config_ids?.[0]
  }
  return undefined
}

/** A friendlier read of a node-reported account. `raw` is the untouched
 *  protocol record — nothing here is hidden or lossy, this just saves every
 *  caller from re-deriving the same handful of fields. AccountKind groups
 *  broker/bank/asset accounts under 'generic': those kinds only exist
 *  client-side (Astrolab's mirror), the node models them as generic. */
export function accountViewOf(na: ProtocolAccount, exchangeConfigs: ExchangeConfig[]): AccountView {
  const specifics = na.specifics
  const type: AccountKind =
    specifics?.account_type === 'exchange'   ? 'exchange' :
    specifics?.account_type === 'blockchain' ? 'wallet' :
    'generic'
  const cfgId = exchangeConfigIdOf(specifics)
  const exchange = cfgId ? exchangeConfigs.find((c) => c.id === cfgId)?.exchange : undefined
  return {
    ...na,
    name: na.name || na.id,
    type,
    exchange,
    simulated: na.is_simulated ?? false,
    connected: na.state?.status !== 'invalid',
    holdings: accountHoldingsFromNodeState(na),
    raw: na,
  }
}

/** A friendlier read of a node-reported automation. `raw` is the untouched
 *  protocol record. `strategy` is recovered from the action history — the
 *  node's own `AutomationState` carries no strategy reference. `name` is a
 *  convenience flattening of `metadata.name`.
 *
 *  `strategyRefs`, when given, is a precomputed `automationStrategyRefsOf(actions)`
 *  used instead of re-deriving the ref from `actions` for this one automation.
 *  Pass it when mapping many automations against the same `actions` array (see
 *  `listWithActions` below) — otherwise each call rescans the full action
 *  history, making the batch O(automations × actions) instead of O(actions). */
export function automationViewOf(
  state: AutomationState,
  actions: UserAction[],
  strategyRefs?: Map<string, { id: string; version?: string }>,
): AutomationView {
  return {
    ...state,
    status: workflowStatusToAutomationStatus(state.status),
    name: state.metadata?.name || state.id,
    accountIds: state.exchange_account_ids ?? [],
    strategy: (strategyRefs ? strategyRefs.get(state.id) : automationStrategyRefOf(actions, state.id)) ?? null,
    error: automationErrorOf(state),
    holdings: automationHoldings(state),
    raw: state,
  }
}
