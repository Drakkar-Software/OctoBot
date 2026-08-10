import type {
  Account as ProtocolAccount,
  ExchangeConfig,
  AutomationState,
  UserAction,
} from '@drakkar.software/octobot-protocol'
import {
  accountHoldingsFromNodeState,
  workflowStatusToAutomationStatus,
  automationErrorOf,
  automationHoldings,
  automationStrategyRefOf,
  type AutomationRunStatus,
  type Holding,
} from '../../protocol/state.js'

export type { Holding }

export type AccountKind = 'exchange' | 'wallet' | 'generic'

/** A friendlier read of a node-reported account. `raw` is the untouched
 *  protocol record — nothing here is hidden or lossy, this just saves every
 *  caller from re-deriving the same handful of fields. */
export type AccountView = {
  id: string
  name: string
  type: AccountKind
  /** Resolved through `exchange_configs` — undefined for non-exchange kinds. */
  exchange?: string
  simulated: boolean
  /** `false` when the node's own validation marked this account invalid
   *  (bad credentials, unreachable venue, …). */
  connected: boolean
  holdings: Holding[]
  raw: ProtocolAccount
}

export function accountViewOf(na: ProtocolAccount, exchangeConfigs: ExchangeConfig[]): AccountView {
  const specifics = na.specifics as { account_type?: string; exchange_config_ids?: string[] } | undefined
  const type: AccountKind =
    specifics?.account_type === 'exchange'   ? 'exchange' :
    specifics?.account_type === 'blockchain' ? 'wallet' :
    'generic'
  const cfgId = specifics?.exchange_config_ids?.[0]
  const exchange = cfgId ? exchangeConfigs.find((c) => c.id === cfgId)?.exchange : undefined
  return {
    id: na.id,
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
 *  node's own `AutomationState` carries no strategy reference. */
export type AutomationView = {
  id: string
  name: string
  status: AutomationRunStatus
  /** Every exchange account this automation trades through. */
  accountIds: string[]
  strategy: { id: string; version?: string } | null
  error: string | null
  assets: Holding[]
  raw: AutomationState
}

export function automationViewOf(state: AutomationState, actions: UserAction[]): AutomationView {
  return {
    id: state.id,
    name: state.metadata?.name || state.id,
    status: workflowStatusToAutomationStatus(state.status),
    accountIds: state.exchange_account_ids ?? [],
    strategy: automationStrategyRefOf(actions, state.id),
    error: automationErrorOf(state),
    assets: automationHoldings(state).map((a) => ({ symbol: a.symbol, total: a.total, free: a.available, used: Math.max(0, a.total - a.available) })),
    raw: state,
  }
}
