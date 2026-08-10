import type {
  Strategy as ProtocolStrategy,
  CreateAutomationConfiguration,
  EditAutomationConfiguration,
  StopAutomationConfiguration,
  AutomationConfiguration,
  AccountAuthentication,
  ExchangeConfig,
  Account as ProtocolAccount,
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
  CreateStrategyConfiguration,
  EditStrategyConfiguration,
  DeleteStrategyConfiguration,
} from '@drakkar.software/octobot-protocol'

export type AutomationBuildInput = {
  name: string
  description?: string
  strategy: ProtocolStrategy
  accountIds: string[]
}

/** A locally-generated id for a queued user action. Not the node's own id
 *  scheme — just a client-side correlation handle for the outbox. */
export function newUserActionId(): string {
  return `ua_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
}

export function buildAutomationConfiguration(input: AutomationBuildInput): AutomationConfiguration {
  const now = new Date().toISOString()
  return {
    name:        input.name,
    description: input.description,
    created_at:  now,
    updated_at:  now,
    strategy:    { id: input.strategy.id, version: input.strategy.version, emit_signals: false },
    accounts:    input.accountIds.map((id) => ({ id })),
  }
}

export function buildCreateAutomationConfig(input: AutomationBuildInput): CreateAutomationConfiguration {
  return {
    action_type:   'automation_create',
    configuration: buildAutomationConfiguration(input),
  }
}

export function buildEditAutomationConfig(input: AutomationBuildInput & { automationId: string }): EditAutomationConfiguration {
  return {
    id:            input.automationId,
    action_type:   'automation_edit',
    configuration: buildAutomationConfiguration(input),
  }
}

export function buildStopAutomationConfig(automationId: string): StopAutomationConfiguration {
  return {
    id:          automationId,
    action_type: 'automation_stop',
  }
}

// ── Strategy user-actions (protocol 0.4.0) ───────────────────────────────────
// The node's StrategyProvider is populated ONLY by strategy user actions — a
// client push of the strategies collection is opaque dead data to it, and
// automation_create loads the strategy from the provider by (id, version).

export function buildCreateStrategyConfig(strategy: ProtocolStrategy): CreateStrategyConfiguration {
  return { action_type: 'strategy_create', configuration: strategy }
}

export function buildEditStrategyConfig(strategy: ProtocolStrategy): EditStrategyConfiguration {
  return { id: strategy.id, action_type: 'strategy_edit', configuration: strategy }
}

export function buildDeleteStrategyConfig(id: string): DeleteStrategyConfiguration {
  return { id, action_type: 'strategy_delete' }
}

// ── Account user-actions (protocol 0.4.0 graph) ──────────────────────────────
// 0.4.0 splits an account across three node-side items: credentials live in
// AccountAuthentication (account_auth_* actions), the venue in ExchangeConfig
// (exchange_config_* actions), and the Account itself only references them
// (authentication_id + specifics.exchange_config_ids). Ids are DERIVED from
// the account id so edits and deletes can address the graph without storing
// extra local fields. The node does not cascade deletes — the client emits
// the auth/config deletes itself.

export function accountAuthIdFor(accountId: string): string {
  return `auth_${accountId}`
}

export function exchangeConfigIdFor(accountId: string): string {
  return `cfg_${accountId}`
}

/** Reverse of `accountAuthIdFor` — recovers the account id an
 *  account_auth_* action's own id refers to. Safe because that helper is the
 *  only producer of `auth_*` ids. */
export function accountIdFromAuthId(authId: string): string {
  return authId.startsWith('auth_') ? authId.slice('auth_'.length) : authId
}

/** Reverse of `exchangeConfigIdFor` — recovers the account id an
 *  exchange_config_* action's own id refers to. Safe because that helper is
 *  the only producer of `cfg_*` ids. */
export function accountIdFromExchangeConfigId(configId: string): string {
  return configId.startsWith('cfg_') ? configId.slice('cfg_'.length) : configId
}

export function buildCreateAccountConfig(account: ProtocolAccount): CreateAccountConfiguration {
  return {
    action_type:   'account_create',
    configuration: account,
  }
}

export function buildEditAccountConfig(id: string, account?: ProtocolAccount): EditAccountConfiguration {
  return {
    id,
    action_type:   'account_edit',
    configuration: account,
  }
}

export function buildDeleteAccountConfig(id: string): DeleteAccountConfiguration {
  return {
    id,
    action_type: 'account_delete',
  }
}

export function buildRefreshAccountsConfig(accountIds?: string[]): RefreshAccountsConfiguration {
  return {
    action_type: 'accounts_refresh',
    ...(accountIds ? { account_ids: accountIds } : {}),
  }
}

export function buildCreateAccountAuthConfig(auth: AccountAuthentication): CreateAccountAuthConfiguration {
  return { action_type: 'account_auth_create', configuration: auth }
}

export function buildEditAccountAuthConfig(auth: AccountAuthentication): EditAccountAuthConfiguration {
  return { id: auth.id, action_type: 'account_auth_edit', configuration: auth }
}

export function buildDeleteAccountAuthConfig(id: string): DeleteAccountAuthConfiguration {
  return { id, action_type: 'account_auth_delete' }
}

export function buildCreateExchangeConfigConfig(config: ExchangeConfig): CreateExchangeConfigConfiguration {
  return { action_type: 'exchange_config_create', configuration: config }
}

export function buildEditExchangeConfigConfig(config: ExchangeConfig): EditExchangeConfigConfiguration {
  return { id: config.id, action_type: 'exchange_config_edit', configuration: config }
}

export function buildDeleteExchangeConfigConfig(id: string): DeleteExchangeConfigConfiguration {
  return { id, action_type: 'exchange_config_delete' }
}
