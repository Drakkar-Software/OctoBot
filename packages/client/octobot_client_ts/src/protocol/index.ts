export {
  protocolStrategyKind,
  parseNodeAutomationStates,
  parseNodeUserActions,
  workflowStatusToAutomationStatus,
  automationErrorOf,
  normalizeNodeAssets,
  automationHoldings,
  parseNodeAccounts,
  parseNodeExchangeConfigs,
  accountHoldingsFromNodeState,
  automationResultOf,
  accountResultOf,
  actionErrorDetails,
  createdAutomationIdOf,
  createdAccountIdOf,
  actionDomainOf,
  targetAutomationIdOf,
  targetAccountIdsOf,
  actionTargetsAccount,
  automationStrategyRefOf,
  actionDisplayName,
  isRecord,
  cachedByDoc,
  type AutomationRunStatus,
  type Holding,
  type UserActionDomain,
} from './state.js'
export {
  newUserActionId,
  buildAutomationConfiguration,
  buildCreateAutomationConfig,
  buildEditAutomationConfig,
  buildStopAutomationConfig,
  buildCreateStrategyConfig,
  buildEditStrategyConfig,
  buildDeleteStrategyConfig,
  accountAuthIdFor,
  exchangeConfigIdFor,
  accountIdFromAuthId,
  accountIdFromExchangeConfigId,
  buildCreateAccountConfig,
  buildEditAccountConfig,
  buildDeleteAccountConfig,
  buildRefreshAccountsConfig,
  buildCreateAccountAuthConfig,
  buildEditAccountAuthConfig,
  buildDeleteAccountAuthConfig,
  buildCreateExchangeConfigConfig,
  buildEditExchangeConfigConfig,
  buildDeleteExchangeConfigConfig,
  type AutomationBuildInput,
} from './actions.js'
export * as strategy from './strategy/index.js'
// Flat re-exports of every symbol the `strategy` namespace above holds — for
// a caller that wants `buildStrategy(...)` directly rather than
// `strategy.buildStrategy(...)`.
export * from './strategy/index.js'
export { baseCurrencyOf } from './symbols.js'
export { sleep, pollDelay } from './poll.js'
export {
  type UserDataState,
  type AccountsState,
  type UserActionsDocument,
  type AccountTradingDocument,
} from './documents.js'
export {
  runCreateAutomation,
  AutomationActionFailedError,
  AutomationTimeoutError,
  type ActionEmitter,
  type CreateAutomationInput,
  type CreateAutomationProgress,
} from './orchestration/createAutomation.js'
export {
  encodeActionProposal,
  decodeActionProposal,
  type ActionProposal,
  type ProposedActionEntry,
} from './proposal.js'
