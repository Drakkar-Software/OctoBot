import type {
  Account,
  AccountAuthentication,
  AccountReference,
  AccountSpecifics,
  AutomationConfiguration,
  AutomationSignalType,
  CopyConfiguration,
  DCAConfiguration,
  CreateAccountAuthConfiguration,
  CreateAccountConfiguration,
  CreateAutomationConfiguration,
  CreateExchangeConfigConfiguration,
  CreateStrategyConfiguration,
  DeleteAccountAuthConfiguration,
  DeleteAccountConfiguration,
  DeleteExchangeConfigConfiguration,
  DeleteStrategyConfiguration,
  EditAccountAuthConfiguration,
  EditAccountConfiguration,
  EditAutomationConfiguration,
  EditExchangeConfigConfiguration,
  EditStrategyConfiguration,
  EvaluatorConfiguration,
  EvaluatorConfigurationConfiguration,
  EMAMomentumEvaluatorConfiguration,
  ExchangeAccount,
  ExchangeConfig,
  GenericProcessConfiguration,
  GridConfiguration,
  IndexConfiguration,
  RefreshAccountsConfiguration,
  RSIMomentumEvaluatorConfiguration,
  SignalAutomationConfiguration,
  SimpleStrategyEvaluatorConfiguration,
  StopAutomationConfiguration,
  Strategy,
  StrategyConfiguration,
  StrategyEvaluatorConfiguration,
  StrategyEvaluatorConfigurationConfiguration,
  StrategyReference,
  UserAction,
  UserActionConfiguration,
  UserActionType,
} from "@/client"

export const DEFAULT_USER_ACTION_TYPE: UserActionType = "automation_stop"

export type UserActionTemplateKey =
  | UserActionType
  | "strategy_create_grid"
  | "strategy_create_index"
  | "strategy_create_copy"
  | "strategy_create_dca"

export const DEFAULT_USER_ACTION_TEMPLATE_KEY: UserActionTemplateKey =
  DEFAULT_USER_ACTION_TYPE

export const USER_ACTION_TEMPLATE_OPTIONS: {
  value: UserActionTemplateKey
  label: string
}[] = [
  { value: "automation_create", label: "Automation create" },
  { value: "automation_edit", label: "Automation edit" },
  { value: "automation_stop", label: "Automation stop" },
  { value: "automation_signal", label: "Automation signal" },
  { value: "account_create", label: "Account create" },
  { value: "account_edit", label: "Account edit" },
  { value: "account_delete", label: "Account delete" },
  { value: "account_auth_create", label: "Account auth create" },
  { value: "account_auth_edit", label: "Account auth edit" },
  { value: "account_auth_delete", label: "Account auth delete" },
  { value: "accounts_refresh", label: "Accounts refresh" },
  { value: "exchange_config_create", label: "Exchange config create" },
  { value: "exchange_config_edit", label: "Exchange config edit" },
  { value: "exchange_config_delete", label: "Exchange config delete" },
  { value: "strategy_create", label: "Strategy create" },
  { value: "strategy_create_grid", label: "Strategy create (grid)" },
  { value: "strategy_create_index", label: "Strategy create (index)" },
  { value: "strategy_create_copy", label: "Strategy create (copy trading)" },
  {
    value: "strategy_create_dca",
    label: "Strategy create (DCA, 2 evaluators)",
  },
  { value: "strategy_edit", label: "Strategy edit" },
  { value: "strategy_delete", label: "Strategy delete" },
]

export const DEFAULT_ACTIONS_SIGNAL_PAYLOAD = `[
  {
    "id": "action_1",
    "dsl_script": "noop()"
  }
]`

export const DEFAULT_TRADING_SIGNAL_PAYLOAD = `{
  "strategy_id": "test-strategy-id",
  "account": {
    "version": "1.0.0",
    "updated_at": 0,
    "copied_assets": []
  }
}`

type DebugUserActionConfiguration =
  | CreateAutomationConfiguration
  | EditAutomationConfiguration
  | StopAutomationConfiguration
  | SignalAutomationConfiguration
  | CreateStrategyConfiguration
  | EditStrategyConfiguration
  | DeleteStrategyConfiguration
  | CreateAccountConfiguration
  | EditAccountConfiguration
  | DeleteAccountConfiguration
  | CreateAccountAuthConfiguration
  | EditAccountAuthConfiguration
  | DeleteAccountAuthConfiguration
  | RefreshAccountsConfiguration
  | CreateExchangeConfigConfiguration
  | EditExchangeConfigConfiguration
  | DeleteExchangeConfigConfiguration

type StrategyConfigurationVariant =
  | GridConfiguration
  | IndexConfiguration
  | CopyConfiguration
  | DCAConfiguration
  | GenericProcessConfiguration

function assertNever(value: never): never {
  throw new Error(`Unexpected value: ${String(value)}`)
}

/** OpenAPI oneOf bridge: runtime JSON uses flat strategy configuration objects. */
function asStrategyConfiguration(
  configuration: StrategyConfigurationVariant,
): StrategyConfiguration {
  return configuration as StrategyConfiguration
}

/** OpenAPI oneOf bridge: runtime JSON uses flat evaluator configuration objects. */
function asEvaluatorConfigurationConfiguration(
  configuration:
    | RSIMomentumEvaluatorConfiguration
    | EMAMomentumEvaluatorConfiguration,
): EvaluatorConfigurationConfiguration {
  return configuration as EvaluatorConfigurationConfiguration
}

/** OpenAPI oneOf bridge: runtime JSON uses flat strategy evaluator configuration objects. */
function asStrategyEvaluatorConfigurationConfiguration(
  configuration: SimpleStrategyEvaluatorConfiguration,
): StrategyEvaluatorConfigurationConfiguration {
  return configuration as StrategyEvaluatorConfigurationConfiguration
}

/** OpenAPI oneOf bridge: runtime JSON uses flat exchange account specifics. */
function asAccountSpecifics(specifics: ExchangeAccount): AccountSpecifics {
  return specifics as AccountSpecifics
}

/** OpenAPI oneOf bridge: runtime JSON uses flat user-action configuration payloads. */
function userAction(
  id: string,
  configuration: DebugUserActionConfiguration,
): UserAction {
  return {
    id,
    configuration: configuration as UserActionConfiguration,
  }
}

function userActionJson(userActionPayload: UserAction): string {
  return JSON.stringify(userActionPayload, null, 2)
}

export function defaultSignalPayloadText(
  signalType: AutomationSignalType,
): string {
  switch (signalType) {
    case "actions":
      return DEFAULT_ACTIONS_SIGNAL_PAYLOAD
    case "trading_signal":
      return DEFAULT_TRADING_SIGNAL_PAYLOAD
    default:
      return ""
  }
}

function currentIsoTimestamp(): string {
  return new Date().toISOString()
}

function newResourceId(): string {
  return crypto.randomUUID()
}

function sampleStrategyReference(
  id = "<strategy-id>",
  emitSignals = false,
): StrategyReference {
  return {
    id,
    version: "1.0.0",
    emit_signals: emitSignals,
  } satisfies StrategyReference
}

function sampleAutomationConfiguration(): AutomationConfiguration {
  return {
    name: "Automation",
    created_at: currentIsoTimestamp(),
    updated_at: null,
    strategy: sampleStrategyReference(),
    accounts: [{ id: "<account-id>" } satisfies AccountReference],
  } satisfies AutomationConfiguration
}

function sampleExchangeAccountSpecifics(): ExchangeAccount {
  return {
    account_type: "exchange",
    remote_account_id: "",
    exchange_config_ids: ["<exchange-config-id>"],
  } satisfies ExchangeAccount
}

function sampleAccountConfiguration(
  id = "<account-id>",
  authId: string | null = null,
): Account {
  return {
    id,
    name: "My account",
    is_simulated: true,
    created_at: currentIsoTimestamp(),
    authentication_id: authId,
    specifics: asAccountSpecifics(sampleExchangeAccountSpecifics()),
  } satisfies Account
}

function sampleAccountAuthConfiguration(
  id = "<account-auth-id>",
): AccountAuthentication {
  return {
    id,
    api_key: null,
    api_secret: null,
    api_passphrase: null,
    public_key: null,
    private_key: null,
    seed_phrase: null,
  } satisfies AccountAuthentication
}

function sampleExchangeConfig(id = "<exchange-config-id>"): ExchangeConfig {
  return {
    id,
    name: "binance-main",
    exchange: "binance",
    sandboxed: false,
  } satisfies ExchangeConfig
}

function sampleStrategyShell(
  id: string,
  name: string,
  configuration: StrategyConfigurationVariant,
  referenceMarket = "USDT",
): Strategy {
  return {
    id,
    version: "1.0.0",
    name,
    reference_market: referenceMarket,
    created_at: currentIsoTimestamp(),
    updated_at: currentIsoTimestamp(),
    configuration: asStrategyConfiguration(configuration),
  } satisfies Strategy
}

function sampleGenericProcessStrategyConfiguration(
  id = "<strategy-id>",
): Strategy {
  return sampleStrategyShell(id, "My strategy", {
    configuration_type: "generic_process",
    profile_data: {},
  } satisfies GenericProcessConfiguration)
}

function sampleGridStrategyConfiguration(id = "<strategy-id>"): Strategy {
  return sampleStrategyShell(id, "My grid strategy", {
    configuration_type: "grid",
    symbol: "BTC/USDT",
    spread: 3000,
    increment: 1000,
    buy_count: 4,
    sell_count: 4,
    enable_trailing_up: false,
    enable_trailing_down: false,
    order_by_order_trailing: false,
  } satisfies GridConfiguration)
}

function sampleIndexStrategyConfiguration(id = "<strategy-id>"): Strategy {
  return sampleStrategyShell(id, "My index strategy", {
    configuration_type: "index",
    coins: [{ name: "BTC", ratio: 1.0 }],
    rebalance_trigger_min_percent: 5.0,
  } satisfies IndexConfiguration)
}

function sampleCopyStrategyConfiguration(id = "<strategy-id>"): Strategy {
  return sampleStrategyShell(id, "My copy trading strategy", {
    configuration_type: "copy",
    strategy_id: "<master-strategy-id>",
  } satisfies CopyConfiguration)
}

const DCA_TRADED_SYMBOLS = ["BTC/USDC", "ETH/USDC"] as const

function sampleDcaStrategyConfiguration(id = "<strategy-id>"): Strategy {
  return sampleStrategyShell(
    id,
    "My DCA strategy (2 evaluators)",
    {
      configuration_type: "dca",
      symbols: [],
      entry_order_amount: "8%t",
      exit_limit_orders_price_percent: 1.75,
      entry_limit_orders_price_percent: 1.5,
      secondary_entry_orders_count: 1,
      secondary_entry_orders_amount: "7%t",
      secondary_entry_orders_price_percent: 1.0,
      enable_stop_loss: false,
      stop_loss_price_discount_percent: 0,
      trigger_mode: "Maximum evaluators signals based",
      use_init_entry_orders: false,
      strategies: [
        {
          time_frames: ["1h"],
          configuration: asStrategyEvaluatorConfigurationConfiguration({
            configuration_type: "SimpleStrategyEvaluator",
          } satisfies SimpleStrategyEvaluatorConfiguration),
        } satisfies StrategyEvaluatorConfiguration,
      ],
      evaluators: [
        {
          symbols: [...DCA_TRADED_SYMBOLS],
          include_in_construction_candle: false,
          configuration: asEvaluatorConfigurationConfiguration({
            configuration_type: "RSIMomentumEvaluator",
            period_length: 12,
            long_threshold: 50,
            short_threshold: 70,
          } satisfies RSIMomentumEvaluatorConfiguration),
        } satisfies EvaluatorConfiguration,
        {
          symbols: [...DCA_TRADED_SYMBOLS],
          include_in_construction_candle: false,
          configuration: asEvaluatorConfigurationConfiguration({
            configuration_type: "EMAMomentumEvaluator",
            period_length: 10,
            price_threshold_percent: 1.0,
            reverse_signal: false,
          } satisfies EMAMomentumEvaluatorConfiguration),
        } satisfies EvaluatorConfiguration,
      ],
    } satisfies DCAConfiguration,
    "USDC",
  )
}

export function buildUserActionTemplate(
  templateKey: UserActionTemplateKey,
): UserAction {
  if (templateKey === "strategy_create_grid") {
    return userAction(
      "ua-manual-strategy_create_grid",
      {
        action_type: "strategy_create",
        configuration: sampleGridStrategyConfiguration(newResourceId()),
      } satisfies CreateStrategyConfiguration,
    )
  }

  if (templateKey === "strategy_create_index") {
    return userAction(
      "ua-manual-strategy_create_index",
      {
        action_type: "strategy_create",
        configuration: sampleIndexStrategyConfiguration(newResourceId()),
      } satisfies CreateStrategyConfiguration,
    )
  }

  if (templateKey === "strategy_create_copy") {
    return userAction(
      "ua-manual-strategy_create_copy",
      {
        action_type: "strategy_create",
        configuration: sampleCopyStrategyConfiguration(newResourceId()),
      } satisfies CreateStrategyConfiguration,
    )
  }

  if (templateKey === "strategy_create_dca") {
    return userAction(
      "ua-manual-strategy_create_dca",
      {
        action_type: "strategy_create",
        configuration: sampleDcaStrategyConfiguration(newResourceId()),
      } satisfies CreateStrategyConfiguration,
    )
  }

  const actionType: UserActionType = templateKey
  const id = `ua-manual-${actionType}`

  switch (actionType) {
    case "automation_create":
      return userAction(id, {
        action_type: actionType,
        configuration: sampleAutomationConfiguration(),
      } satisfies CreateAutomationConfiguration)
    case "automation_edit":
      return userAction(id, {
        action_type: actionType,
        id: "<automation-id>",
        configuration: sampleAutomationConfiguration(),
      } satisfies EditAutomationConfiguration)
    case "automation_stop":
      return userAction(id, {
        action_type: actionType,
        id: "<automation-id>",
      } satisfies StopAutomationConfiguration)
    case "automation_signal":
      return userAction(id, {
        action_type: actionType,
        automation_id: "<automation-id>",
        signal_type: "forced_trigger",
      } satisfies SignalAutomationConfiguration)
    case "account_create":
      return userAction(id, {
        action_type: actionType,
        configuration: sampleAccountConfiguration(newResourceId()),
      } satisfies CreateAccountConfiguration)
    case "account_edit":
      return userAction(id, {
        action_type: actionType,
        id: "<account-id>",
        configuration: sampleAccountConfiguration(
          "<account-id>",
          "<account-auth-id>",
        ),
      } satisfies EditAccountConfiguration)
    case "account_delete":
      return userAction(id, {
        action_type: actionType,
        id: "<account-id>",
      } satisfies DeleteAccountConfiguration)
    case "account_auth_create":
      return userAction(id, {
        action_type: actionType,
        configuration: sampleAccountAuthConfiguration(newResourceId()),
      } satisfies CreateAccountAuthConfiguration)
    case "account_auth_edit":
      return userAction(id, {
        action_type: actionType,
        id: "<account-auth-id>",
        configuration: sampleAccountAuthConfiguration(),
      } satisfies EditAccountAuthConfiguration)
    case "account_auth_delete":
      return userAction(id, {
        action_type: actionType,
        id: "<account-auth-id>",
      } satisfies DeleteAccountAuthConfiguration)
    case "accounts_refresh":
      return userAction(id, {
        action_type: actionType,
        account_ids: ["<account-id>"],
      } satisfies RefreshAccountsConfiguration)
    case "exchange_config_create":
      return userAction(id, {
        action_type: actionType,
        configuration: sampleExchangeConfig(newResourceId()),
      } satisfies CreateExchangeConfigConfiguration)
    case "exchange_config_edit":
      return userAction(id, {
        action_type: actionType,
        id: "<exchange-config-id>",
        configuration: sampleExchangeConfig(),
      } satisfies EditExchangeConfigConfiguration)
    case "exchange_config_delete":
      return userAction(id, {
        action_type: actionType,
        id: "<exchange-config-id>",
      } satisfies DeleteExchangeConfigConfiguration)
    case "strategy_create":
      return userAction(id, {
        action_type: actionType,
        configuration: sampleGenericProcessStrategyConfiguration(newResourceId()),
      } satisfies CreateStrategyConfiguration)
    case "strategy_edit":
      return userAction(id, {
        action_type: actionType,
        id: "<strategy-id>",
        configuration: sampleGenericProcessStrategyConfiguration(),
      } satisfies EditStrategyConfiguration)
    case "strategy_delete":
      return userAction(id, {
        action_type: actionType,
        id: "<strategy-id>",
      } satisfies DeleteStrategyConfiguration)
    default:
      return assertNever(actionType)
  }
}

export function buildUserActionTemplateJson(
  templateKey: UserActionTemplateKey,
): string {
  return userActionJson(buildUserActionTemplate(templateKey))
}

export function userActionTemplateKeyFromActionType(
  actionType: UserActionType,
): UserActionTemplateKey {
  return actionType
}

export function buildAccountEditUserActionJson(account: Account): string {
  return userActionJson(
    userAction(`ua-edit-${account.id}`, {
      action_type: "account_edit",
      id: account.id,
      configuration: account,
    } satisfies EditAccountConfiguration),
  )
}

export function buildExchangeConfigEditUserActionJson(
  config: ExchangeConfig,
): string {
  return userActionJson(
    userAction(`ua-edit-${config.id}`, {
      action_type: "exchange_config_edit",
      id: config.id,
      configuration: config,
    } satisfies EditExchangeConfigConfiguration),
  )
}

export function buildStrategyEditUserActionJson(strategy: Strategy): string {
  return userActionJson(
    userAction(`ua-edit-${strategy.id}`, {
      action_type: "strategy_edit",
      id: strategy.id,
      configuration: strategy,
    } satisfies EditStrategyConfiguration),
  )
}

export function buildAutomationStopUserActionJson(automationId: string): string {
  return userActionJson(
    userAction(`ua-stop-${automationId}`, {
      action_type: "automation_stop",
      id: automationId,
    } satisfies StopAutomationConfiguration),
  )
}

export function buildAutomationSignalUserActionJson(
  automationId: string,
  signalType: AutomationSignalType = "forced_trigger",
): string {
  return userActionJson(
    userAction(`ua-signal-${automationId}`, {
      action_type: "automation_signal",
      automation_id: automationId,
      signal_type: signalType,
    } satisfies SignalAutomationConfiguration),
  )
}

export function buildAutomationCreateUserActionJsonForAccount(
  account: Account,
): string {
  const automationName = account.name || "Automation"
  return userActionJson(
    userAction(`ua-create-automation-account-${account.id}`, {
      action_type: "automation_create",
      configuration: {
        ...sampleAutomationConfiguration(),
        name: automationName,
        accounts: [{ id: account.id } satisfies AccountReference],
      },
    } satisfies CreateAutomationConfiguration),
  )
}

export function buildAutomationCreateUserActionJsonForStrategy(
  strategy: Strategy,
): string {
  const automationName = strategy.name || "Automation"
  return userActionJson(
    userAction(`ua-create-automation-strategy-${strategy.id}`, {
      action_type: "automation_create",
      configuration: {
        ...sampleAutomationConfiguration(),
        name: automationName,
        strategy: {
          id: strategy.id,
          version: strategy.version,
          emit_signals: false,
        } satisfies StrategyReference,
      },
    } satisfies CreateAutomationConfiguration),
  )
}
